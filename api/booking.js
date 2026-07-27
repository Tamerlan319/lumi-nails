export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ ok: false, error: 'Method not allowed' })
  }

  const { name, phone, service, date, time } = req.body || {}
  if (!name || !phone) {
    return res.status(400).json({ ok: false, error: 'Имя и телефон обязательны' })
  }

  const token = process.env.TELEGRAM_BOT_TOKEN
  const chatId = process.env.TELEGRAM_CHAT_ID

  if (token && chatId) {
    const text = [
      '💅 Новая запись LUMI NAILS',
      `Имя: ${name}`,
      `Телефон: ${phone}`,
      `Услуга: ${service || 'не выбрана'}`,
      `Дата: ${date || 'не выбрана'}`,
      `Время: ${time || 'не выбрано'}`
    ].join('\n')

    try {
      const response = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id: chatId, text })
      })
      if (!response.ok) console.error('Telegram error:', await response.text())
    } catch (error) {
      console.error('Telegram request failed:', error)
    }
  }

  return res.status(200).json({ ok: true })
}
