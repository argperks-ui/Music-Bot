const express = require('express');
const path = require('path');
const axios = require('axios');
const app = express();
const PORT = process.env.PORT || 3000;
const BOT_API = 'http://127.0.0.1:5000/api';

app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.json());

// Routes
app.get('/dashboard', async (req, res) => {
  try {
    const response = await axios.get(`${BOT_API}/state`);
    res.render('dashboard', { botState: response.data });
  } catch (err) {
    res.render('dashboard', { botState: null, error: 'Bot API offline. Run python bot.py first.' });
  }
});

app.get('/guilds', (req, res) => res.render('guilds'));
app.get('/logs', (req, res) => res.render('logs'));
app.get('/library', (req, res) => res.render('library'));

// API Control Proxy
app.post('/api/control', async (req, res) => {
  try {
    const response = await axios.post(`${BOT_API}/control`, req.body);
    res.json(response.data);
  } catch (err) {
    res.status(500).json({ success: false, message: 'Failed to communicate with bot backend.' });
  }
});

app.listen(PORT, () => {
  console.log(`🚀 Cyber Dashboard listening on http://localhost:${PORT}`);
});