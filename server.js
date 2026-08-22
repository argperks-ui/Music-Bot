require('dotenv').config();
const express = require('express');
const session = require('express-session');
const cookieParser = require('cookie-parser');
const path = require('path');
const fs = require('fs');
const http = require('http');
const { Server } = require('socket.io');
const Database = require('better-sqlite3');

const app = express();
app.set('trust proxy', 1); // Fixes session cookies behind Render's proxy
const server = http.createServer(app);
const io = new Server(server);

// ── Multi-Owner Helper ─────────────────────────────────────────────────────
function isOwner(userId) {
  if (!userId) return false;
  const rawOwners = process.env.OWNER_IDS || process.env.OWNER_ID || '';
  const ownerIds = rawOwners.split(',').map(id => id.trim());
  return ownerIds.includes(userId);
}

// ── Ensure data directory exists (Must be before Database Setup) ───────────
if (!fs.existsSync(path.join(__dirname, 'data'))) {
  fs.mkdirSync(path.join(__dirname, 'data'));
}

// ── Database Setup ──────────────────────────────────────────────────────────
const db = new Database(path.join(__dirname, 'data', 'dashboard.db'));
db.pragma('journal_mode = WAL');

db.exec(`
  CREATE TABLE IF NOT EXISTS stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command TEXT NOT NULL,
    guild_id TEXT,
    user_id TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
  );
  CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id TEXT PRIMARY KEY,
    prefix TEXT DEFAULT '!',
    volume INTEGER DEFAULT 50,
    dj_role TEXT DEFAULT '',
    allow_nsfw INTEGER DEFAULT 0,
    stay_24_7 INTEGER DEFAULT 0,
    default_channel TEXT DEFAULT ''
  );
  CREATE TABLE IF NOT EXISTS uptime_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
  );
`);

// ── Middleware ──────────────────────────────────────────────────────────────
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(cookieParser());
app.use(session({
  secret: process.env.SESSION_SECRET || 'git-music-secret',
  resave: false,
  saveUninitialized: false,
  cookie: { secure: true, maxAge: 24 * 60 * 60 * 1000 }
}));

// 🌟 Global View Variables Middleware (Prevents all missing variable errors permanently)
app.use((req, res, next) => {
  res.locals.title = 'Git Music Dashboard';
  res.locals.active = '';
  res.locals.user = req.session.user || null;
  res.locals.hbOnline = true;
  res.locals.bot = null;
  res.locals.guilds = [];
  res.locals.voice = 0;
  res.locals.apiLatency = 0;
  res.locals.heartbeat = { voiceCount: 0, ping: 0 };
  res.locals.nodeVer = process.version;
  res.locals.platform = process.platform;
  res.locals.memory = { heapUsed: 0, heapTotal: 0, rss: 0 };
  
  const clientId = process.env.DISCORD_CLIENT_ID || process.env.CLIENT_ID || '';
  res.locals.INVITE = `https://discord.com/api/oauth2/authorize?client_id=${clientId}&permissions=8&scope=bot%20applications.commands`;
  res.locals.configError = !process.env.DISCORD_BOT_TOKEN || !clientId;
  
  next();
});

app.use(express.static(path.join(__dirname, 'public')));
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

// ── Discord API Helper ─────────────────────────────────────────────────────
const DISCORD_API = 'https://discord.com/api/v10';

async function discordFetch(endpoint, tokenType = 'bot') {
  const token = tokenType === 'bot' 
    ? `Bot ${process.env.DISCORD_BOT_TOKEN}`
    : tokenType;
  
  const res = await fetch(`${DISCORD_API}${endpoint}`, {
    headers: { Authorization: token, 'Content-Type': 'application/json' }
  });
  if (!res.ok) {
    const err = await res.text();
    console.error(`Discord API error ${res.status}: ${err}`);
    return null;
  }
  return res.json();
}

// ── Auth Middleware ─────────────────────────────────────────────────────────
async function requireAuth(req, res, next) {
  if (!req.session.user) return res.redirect('/login');
  
  if (!isOwner(req.session.user.id)) {
    return res.status(403).send('Access denied. You are not the bot owner.');
  }
  next();
}

// ── Routes ─────────────────────────────────────────────────────────────────

app.get('/login', (req, res) => {
  if (req.session.user && isOwner(req.session.user.id)) {
    return res.redirect('/dashboard');
  }
  res.render('login', { 
    title: 'Login',
    clientId: process.env.DISCORD_CLIENT_ID || process.env.CLIENT_ID,
    callbackUrl: process.env.CALLBACK_URL
  });
});

app.get('/auth/callback', async (req, res) => {
  const { code } = req.query;
  if (!code) return res.redirect('/login');

  try {
    const tokenRes = await fetch('https://discord.com/api/oauth2/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        client_id: process.env.DISCORD_CLIENT_ID || process.env.CLIENT_ID,
        client_secret: process.env.DISCORD_CLIENT_SECRET || process.env.CLIENT_SECRET,
        code,
        grant_type: 'authorization_code',
        redirect_uri: process.env.CALLBACK_URL,
        scope: 'identify guilds'
      })
    });
    
    const tokenData = await tokenRes.json();
    if (!tokenData.access_token) {
      return res.redirect('/login?error=failed');
    }

    const userData = await discordFetch('/users/@me', `Bearer ${tokenData.access_token}`);
    
    req.session.user = {
      id: userData.id,
      username: userData.username,
      discriminator: userData.discriminator,
      avatar: userData.avatar,
      global_name: userData.global_name
    };
    
    req.session.accessToken = tokenData.access_token;
    
    if (!isOwner(userData.id)) {
      return res.status(403).render('login', { 
        title: 'Login',
        clientId: process.env.DISCORD_CLIENT_ID || process.env.CLIENT_ID,
        callbackUrl: process.env.CALLBACK_URL,
        error: 'This dashboard is private. You are not authorized.'
      });
    }
    
    res.redirect('/dashboard');
  } catch (err) {
    console.error('OAuth error:', err);
    res.redirect('/login?error=exception');
  }
});

app.get('/logout', (req, res) => {
  req.session.destroy();
  res.redirect('/login');
});

app.get('/', requireAuth, (req, res) => res.redirect('/dashboard'));

app.get('/dashboard', requireAuth, async (req, res) => {
  try {
    const botUser = await discordFetch('/users/@me');
    const botGuilds = await discordFetch('/users/@me/guilds') || [];
    
    const totalGuilds = Array.isArray(botGuilds) ? botGuilds.length : 0;
    
    let totalMembers = 0;
    let voiceConnections = 0;
    
    // ⚡ Optimized parallel fetching with Promise.all
    if (Array.isArray(botGuilds) && botGuilds.length > 0) {
      const guildsToFetch = botGuilds.slice(0, 50);
      const guildPromises = guildsToFetch.map(g => discordFetch(`/guilds/${g.id}?with_counts=true`));
      const fetchedGuilds = await Promise.all(guildPromises);
      
      for (const guild of fetchedGuilds) {
        if (guild && guild.approximate_member_count) {
          totalMembers += guild.approximate_member_count;
        }
      }
    }

    const today = new Date().toISOString().split('T')[0];
    const row = db.prepare("SELECT COUNT(*) as count FROM stats WHERE DATE(timestamp) = ?").get(today);
    const todayCommands = row ? row.count : 0;
    
    const totalRow = db.prepare("SELECT COUNT(*) as count FROM stats").get();
    const totalCommands = totalRow ? totalRow.count : 0;
    
    const uptimeRow = db.prepare("SELECT timestamp FROM uptime_log WHERE event = 'startup' ORDER BY id DESC LIMIT 1").get();
    let uptime = 'N/A';
    if (uptimeRow) {
      const startTime = new Date(uptimeRow.timestamp + 'Z');
      const diff = Date.now() - startTime.getTime();
      const hours = Math.floor(diff / 3600000);
      const minutes = Math.floor((diff % 3600000) / 60000);
      uptime = `${hours}h ${minutes}m`;
    }
    
    const pingStart = Date.now();
    await discordFetch('/gateway');
    const ping = Date.now() - pingStart;

    const memUsage = process.memoryUsage();
    const memory = {
      heapUsed: Math.round(memUsage.heapUsed / 1024 / 1024 * 100) / 100,
      heapTotal: Math.round(memUsage.heapTotal / 1024 / 1024 * 100) / 100,
      rss: Math.round(memUsage.rss / 1024 / 1024 * 100) / 100
    };

    res.render('dashboard', {
      title: 'Dashboard',
      bot: botUser,
      guilds: botGuilds,
      botUser,
      totalGuilds,
      totalMembers,
      voiceConnections,
      voice: voiceConnections,
      heartbeat: { voiceCount: voiceConnections, ping: ping },
      apiLatency: ping,
      nodeVer: process.version,
      platform: process.platform,
      memory,
      todayCommands,
      totalCommands,
      uptime,
      ping,
      active: 'dashboard'
    });
  } catch (err) {
    console.error('Dashboard error:', err);
    res.status(500).send('Error loading dashboard');
  }
});

app.get('/guilds', requireAuth, async (req, res) => {
  try {
    const botGuilds = await discordFetch('/users/@me/guilds') || [];
    
    // ⚡ Optimized parallel fetching for server list page too
    const guildsToFetch = botGuilds.slice(0, 100);
    const guildPromises = guildsToFetch.map(g => discordFetch(`/guilds/${g.id}?with_counts=true`));
    const fetchedGuilds = await Promise.all(guildPromises);

    const enriched = guildsToFetch.map((g, index) => {
      const guild = fetchedGuilds[index];
      return {
        id: g.id,
        name: guild ? guild.name : g.name,
        icon: guild ? guild.icon : g.icon,
        memberCount: guild ? guild.approximate_member_count : '?',
        ownerId: guild ? guild.owner_id : '',
      };
    });

    res.render('guilds', {
      title: 'Servers',
      guilds: enriched,
      active: 'guilds'
    });
  } catch (err) {
    console.error('Guilds error:', err);
    res.status(500).send('Error loading guilds');
  }
});

app.get('/guild/:id', requireAuth, async (req, res) => {
  try {
    const guild = await discordFetch(`/guilds/${req.params.id}?with_counts=true`);
    if (!guild) return res.status(404).send('Guild not found');
    
    const channels = await discordFetch(`/guilds/${req.params.id}/channels`) || [];
    
    const settings = db.prepare("SELECT * FROM guild_settings WHERE guild_id = ?").get(req.params.id);
    const defaultSettings = {
      guild_id: req.params.id,
      prefix: '!',
      volume: 50,
      dj_role: '',
      allow_nsfw: 0,
      stay_24_7: 0,
      default_channel: ''
    };

    res.render('guild', {
      title: 'Guild Settings',
      guild,
      channels: channels.filter(c => c.type === 0 || c.type === 2 || c.type === 5),
      textChannels: channels.filter(c => c.type === 0 || c.type === 5),
      voiceChannels: channels.filter(c => c.type === 2),
      settings: settings || defaultSettings,
      active: 'guilds'
    });
  } catch (err) {
    console.error('Guild detail error:', err);
    res.status(500).send('Error loading guild');
  }
});

app.post('/api/guild/:id/settings', requireAuth, async (req, res) => {
  try {
    const { prefix, volume, dj_role, allow_nsfw, stay_24_7, default_channel } = req.body;
    db.prepare(`
      INSERT INTO guild_settings (guild_id, prefix, volume, dj_role, allow_nsfw, stay_24_7, default_channel)
      VALUES (?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(guild_id) DO UPDATE SET
        prefix = excluded.prefix,
        volume = excluded.volume,
        dj_role = excluded.dj_role,
        allow_nsfw = excluded.allow_nsfw,
        stay_24_7 = excluded.stay_24_7,
        default_channel = excluded.default_channel
    `).run(req.params.id, prefix || '!', parseInt(volume) || 50, dj_role || '', 
           allow_nsfw ? 1 : 0, stay_24_7 ? 1 : 0, default_channel || '');
    
    res.json({ success: true });
  } catch (err) {
    console.error('Settings error:', err);
    res.status(500).json({ success: false, error: err.message });
  }
});

app.get('/analytics', requireAuth, async (req, res) => {
  try {
    const dailyStats = db.prepare(`
      SELECT DATE(timestamp) as date, COUNT(*) as count
      FROM stats
      WHERE timestamp >= DATE('now', '-7 days')
      GROUP BY DATE(timestamp)
      ORDER BY date
    `).all();
    
    const topCommands = db.prepare(`
      SELECT command, COUNT(*) as count
      FROM stats
      GROUP BY command
      ORDER BY count DESC
      LIMIT 10
    `).all();
    
    const hourlyStats = db.prepare(`
      SELECT CAST(strftime('%H', timestamp) AS INTEGER) as hour, COUNT(*) as count
      FROM stats
      GROUP BY hour
      ORDER BY hour
    `).all();

    const totalRow = db.prepare("SELECT COUNT(*) as count FROM stats").get();
    const today = new Date().toISOString().split('T')[0];
    const todayRow = db.prepare("SELECT COUNT(*) as count FROM stats WHERE DATE(timestamp) = ?").get(today);

    res.render('analytics', {
      title: 'Analytics',
      dailyStats: JSON.stringify(dailyStats),
      topCommands: JSON.stringify(topCommands),
      hourlyStats: JSON.stringify(hourlyStats),
      totalCommands: totalRow ? totalRow.count : 0,
      todayCommands: todayRow ? todayRow.count : 0,
      active: 'analytics'
    });
  } catch (err) {
    console.error('Analytics error:', err);
    res.status(500).send('Error loading analytics');
  }
});

app.get('/logs', requireAuth, async (req, res) => {
  try {
    const logs = db.prepare(`
      SELECT * FROM stats ORDER BY timestamp DESC LIMIT 100
    `).all();
    
    res.render('logs', {
      title: 'Logs',
      logs,
      active: 'logs'
    });
  } catch (err) {
    console.error('Logs error:', err);
    res.status(500).send('Error loading logs');
  }
});

app.post('/api/stats/update', (req, res) => {
  const { command, guild_id, user_id } = req.body;
  if (!command) return res.status(400).json({ error: 'command is required' });
  
  const auth = req.headers.authorization;
  if (auth !== `Bearer ${process.env.DISCORD_BOT_TOKEN}`) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  
  try {
    db.prepare("INSERT INTO stats (command, guild_id, user_id) VALUES (?, ?, ?)")
      .run(command, guild_id || 'unknown', user_id || 'unknown');
    
    io.emit('new_command', { command, guild_id, user_id, timestamp: new Date().toISOString() });
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

app.get('/api/stats/overview', requireAuth, async (req, res) => {
  try {
    const botUser = await discordFetch('/users/@me');
    const botGuilds = await discordFetch('/users/@me/guilds');
    const totalGuilds = Array.isArray(botGuilds) ? botGuilds.length : 0;
    
    const today = new Date().toISOString().split('T')[0];
    const row = db.prepare("SELECT COUNT(*) as count FROM stats WHERE DATE(timestamp) = ?").get(today);
    const todayCommands = row ? row.count : 0;
    
    const totalRow = db.prepare("SELECT COUNT(*) as count FROM stats").get();
    
    const pingStart = Date.now();
    await discordFetch('/gateway');
    const ping = Date.now() - pingStart;
    
    res.json({
      guilds: totalGuilds,
      todayCommands,
      totalCommands: totalRow ? totalRow.count : 0,
      ping,
      botName: botUser ? botUser.username : 'Git Music'
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/logs/recent', requireAuth, (req, res) => {
  const logs = db.prepare("SELECT * FROM stats ORDER BY timestamp DESC LIMIT 20").all();
  res.json(logs);
});

app.get('/api/bot/status', requireAuth, async (req, res) => {
  try {
    const botUser = await discordFetch('/users/@me');
    const botGuilds = await discordFetch('/users/@me/guilds');
    const memUsage = process.memoryUsage();
    
    const uptimeRow = db.prepare("SELECT timestamp FROM uptime_log WHERE event = 'startup' ORDER BY id DESC LIMIT 1").get();
    let uptimeSeconds = 0;
    if (uptimeRow) {
      uptimeSeconds = Math.floor((Date.now() - new Date(uptimeRow.timestamp + 'Z').getTime()) / 1000);
    }

    const pingStart = Date.now();
    await discordFetch('/gateway');
    const ping = Date.now() - pingStart;
    
    res.json({
      name: botUser ? botUser.username : 'Git Music',
      avatar: botUser ? `https://cdn.discordapp.com/avatars/${botUser.id}/${botUser.avatar}.png` : '',
      id: botUser ? botUser.id : '',
      guilds: Array.isArray(botGuilds) ? botGuilds.length : 0,
      ping,
      memory: {
        heapUsed: Math.round(memUsage.heapUsed / 1024 / 1024 * 100) / 100,
        heapTotal: Math.round(memUsage.heapTotal / 1024 / 1024 * 100) / 100,
        rss: Math.round(memUsage.rss / 1024 / 1024 * 100) / 100
      },
      uptime: uptimeSeconds,
      nodeVersion: process.version,
      platform: process.platform
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

io.on('connection', (socket) => {
  console.log('Client connected to socket');
  const logs = db.prepare("SELECT * FROM stats ORDER BY timestamp DESC LIMIT 10").all();
  socket.emit('initial_logs', logs);
  
  socket.on('disconnect', () => {
    console.log('Client disconnected');
  });
});

db.prepare("INSERT INTO uptime_log (event) VALUES ('startup')").run();

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`🎵 Git Music Dashboard running at http://localhost:${PORT}`);
  console.log(`📊 Login at http://localhost:${PORT}/login`);
});