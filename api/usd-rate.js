const CBR_XML_URL = 'https://www.cbr.ru/scripts/XML_daily.asp';
const FALLBACK_JSON_URL = 'https://www.cbr-xml-daily.ru/daily_json.js';

function decodeXml(text = '') {
  return text
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&');
}

function parseCbrXml(xml) {
  const dateMatch = xml.match(/<ValCurs[^>]*Date="([^"]+)"/i);
  const blocks = xml.match(/<Valute\b[\s\S]*?<\/Valute>/gi) || [];
  const usdBlock = blocks.find(block => /<CharCode>\s*USD\s*<\/CharCode>/i.test(block));

  if (!usdBlock) throw new Error('USD not found in CBR response');

  const nominalMatch = usdBlock.match(/<Nominal>\s*([^<]+)\s*<\/Nominal>/i);
  const valueMatch = usdBlock.match(/<Value>\s*([^<]+)\s*<\/Value>/i);

  const nominal = Number((nominalMatch?.[1] || '1').replace(',', '.'));
  const value = Number(decodeXml(valueMatch?.[1] || '').replace(',', '.'));
  const rate = value / nominal;

  if (!Number.isFinite(rate) || rate <= 0) {
    throw new Error('Invalid USD rate in CBR response');
  }

  return {
    rate,
    date: dateMatch?.[1] || null,
    source: 'Банк России'
  };
}

async function getFromCbr() {
  const response = await fetch(CBR_XML_URL, {
    headers: { 'User-Agent': 'Mozilla/5.0' }
  });

  if (!response.ok) throw new Error(`CBR HTTP ${response.status}`);
  return parseCbrXml(await response.text());
}

async function getFromFallback() {
  const response = await fetch(FALLBACK_JSON_URL);
  if (!response.ok) throw new Error(`Fallback HTTP ${response.status}`);

  const data = await response.json();
  const rate = Number(data?.Valute?.USD?.Value);
  if (!Number.isFinite(rate) || rate <= 0) throw new Error('Invalid fallback rate');

  return {
    rate,
    date: data?.Date || null,
    source: 'Курс Банка России'
  };
}

export default async function handler(req, res) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return res.status(405).json({ ok: false, error: 'Method not allowed' });
  }

  try {
    let data;
    try {
      data = await getFromCbr();
    } catch (primaryError) {
      console.error('Primary rate source failed:', primaryError);
      data = await getFromFallback();
    }

    res.setHeader('Cache-Control', 's-maxage=1800, stale-while-revalidate=3600');
    return res.status(200).json({
      ok: true,
      rate: Number(data.rate.toFixed(4)),
      date: data.date,
      source: data.source,
      fetchedAt: new Date().toISOString()
    });
  } catch (error) {
    console.error('USD rate error:', error);
    return res.status(502).json({
      ok: false,
      error: 'Не удалось получить актуальный курс доллара'
    });
  }
};
