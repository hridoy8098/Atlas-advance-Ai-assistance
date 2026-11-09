import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Globe, Newspaper, TrendingUp, Landmark, RefreshCw } from 'lucide-react'
import { getBDNews, getBDCurrency, getBDStock, getBDPrayer } from '../../services/api'

const divisions = [
  { name: 'Dhaka', area: 'পৃথক', pop: '২.৩ কোটি' },
  { name: 'Chittagong', area: 'পৃথক', pop: '৩.৩ কোটি' },
  { name: 'Rajshahi', area: 'পৃথক', pop: '২.০ কোটি' },
  { name: 'Khulna', area: 'পৃথক', pop: '১.৭ কোটি' },
  { name: 'Barisal', area: 'পৃথক', pop: '৯০ লক্ষ' },
  { name: 'Sylhet', area: 'পৃথক', pop: '১.১ কোটি' },
  { name: 'Rangpur', area: 'পৃথক', pop: '১.৮ কোটি' },
  { name: 'Mymensingh', area: 'পৃথক', pop: '১.২ কোটি' },
]

const verse = (published) => {
  try {
    const d = new Date(published)
    return isNaN(d) ? published : d.toLocaleString()
  } catch { return published }
}

const hostOf = (link) => {
  try { return new URL(link).hostname.replace('www.', '') } catch { return 'source' }
}

const districts = [
  { name: 'Dhaka', bn: 'ঢাকা', desc: 'জাতীয় রাজধানী, ২৩০০ বছর পুরনো' },
  { name: 'Sylhet', bn: 'সিলেট', desc: 'চা বাগান ও প্রাকৃতিক সৌন্দর্যের দেশ' },
  { name: 'Cox\'s Bazar', bn: 'কক্সবাজার', desc: 'বিশ্বের দীর্ঘতম সমুদ্র সৈকত (১২০ কিমি)' },
  { name: 'Sundarbans', bn: 'সুন্দরবন', desc: 'বিশ্বের বৃহত্তম ম্যানগ্রোভ বন' },
]

export default function BangladeshPanel() {
  const [activeTab, setActiveTab] = useState('overview')
  const [news, setNews] = useState([])
  const [currency, setCurrency] = useState(null)
  const [prayer, setPrayer] = useState(null)
  const [stocks, setStocks] = useState([])
  const [loading, setLoading] = useState({ news: false, economy: false, prayer: false })
  const [error, setError] = useState('')

  const loadNews = async () => {
    setLoading(l => ({ ...l, news: true }))
    try {
      const res = await getBDNews(12)
      setNews(res?.success ? (res.news || []) : [])
      setError(res?.success ? '' : (res?.error || ''))
    } catch (e) { setError(e.message); setNews([]) }
    setLoading(l => ({ ...l, news: false }))
  }

  const loadPrayer = async () => {
    setLoading(l => ({ ...l, prayer: true }))
    try {
      const res = await getBDPrayer('Dhaka')
      setPrayer(res?.success ? res : null)
    } catch { setPrayer(null) }
    setLoading(l => ({ ...l, prayer: false }))
  }

  const loadEconomy = async () => {
    setLoading(l => ({ ...l, economy: true }))
    try {
      const [curRes, stockRes] = await Promise.allSettled([getBDCurrency('BDT'), getBDStock(10)])
      if (curRes.status === 'fulfilled' && curRes.value?.success) setCurrency(curRes.value)
      if (stockRes.status === 'fulfilled' && stockRes.value?.success) setStocks(stockRes.value.stocks || [])
    } catch (e) { setError(e.message) }
    setLoading(l => ({ ...l, economy: false }))
  }

  useEffect(() => {
    loadPrayer()
    loadNews()
    loadEconomy()
  }, [])

  const currencies = currency?.bdt_per_unit
    ? Object.entries(currency.bdt_per_unit).slice(0, 6)
    : []
  const timings = prayer?.timings || {}

  const tabs = [
    { id: 'overview', label: 'OVERVIEW', icon: Globe },
    { id: 'news', label: 'NEWS', icon: Newspaper },
    { id: 'economy', label: 'ECONOMY', icon: TrendingUp },
    { id: 'divisions', label: 'DIVISIONS', icon: Landmark },
  ]

  return (
    <div style={{ display: 'grid', gridTemplateRows: 'auto 1fr', gap: 12, height: '100%' }}>
      <div style={{ display: 'flex', gap: 6 }}>
        {tabs.map(tab => (
          <motion.button key={tab.id} whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
            onClick={() => setActiveTab(tab.id)}
            style={{
              ...S.tab,
              background: activeTab === tab.id ? 'rgba(0,255,200,0.1)' : 'transparent',
              borderColor: activeTab === tab.id ? 'rgba(0,255,200,0.4)' : 'rgba(0,255,200,0.12)',
              color: activeTab === tab.id ? 'var(--cyan)' : 'var(--text-dim)',
            }}>
            <tab.icon size={14} />
            <span style={{ fontSize: 10, letterSpacing: 1 }}>{tab.label}</span>
          </motion.button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {activeTab === 'overview' && (
          <motion.div key="overview" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: 10, height: '100%' }}>
            <div style={S.mainCard}>
              <div style={{ fontFamily: 'Orbitron', fontSize: 10, color: 'var(--text-dim)', letterSpacing: 2, marginBottom: 12 }}>
                🇧🇩 BANGLADESH
              </div>
              <div style={{ fontFamily: 'Share Tech Mono', fontSize: 22, color: 'var(--cyan)', marginBottom: 4 }}>গণপ্রজাতন্ত্রী বাংলাদেশ</div>
              <div style={{ fontSize: 12, color: 'rgba(0,255,200,0.6)' }}>People's Republic of Bangladesh</div>
              <div style={{ display: 'flex', gap: 24, marginTop: 16 }}>
                <div><div style={{ fontFamily: 'Share Tech Mono', fontSize: 18, color: '#00ffc8' }}>১৭.৪ কোটি</div><div style={{ fontSize: 9, color: 'var(--text-dim)' }}>জনসংখ্যা</div></div>
                <div><div style={{ fontFamily: 'Share Tech Mono', fontSize: 18, color: '#00aaff' }}>১,৪৭,৫৭০ km²</div><div style={{ fontSize: 9, color: 'var(--text-dim)' }}>আয়তন</div></div>
              </div>
              <div style={{ display: 'flex', gap: 24, marginTop: 10 }}>
                <div><div style={{ fontFamily: 'Share Tech Mono', fontSize: 18, color: '#ff88ff' }}>ঢাকা</div><div style={{ fontSize: 9, color: 'var(--text-dim)' }}>রাজধানী</div></div>
                  <div><div style={{ fontFamily: 'Share Tech Mono', fontSize: 18, color: '#ffaa00' }}>বাংলা</div><div style={{ fontSize: 9, color: 'var(--text-dim)' }}>জাতীয় ভাষা</div></div>
              </div>

              <div style={{ marginTop: 'auto', paddingTop: 12, borderTop: '1px solid rgba(0,255,200,0.12)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <span style={{ fontFamily: 'Orbitron', fontSize: 9, color: 'var(--text-dim)', letterSpacing: 2 }}>
                    PRAYER · {prayer?.city || 'Dhaka'}{prayer?.date ? ` · ${prayer.date}` : ''}
                  </span>
                  <motion.button whileHover={{ scale: 1.1, rotate: 90 }} whileTap={{ scale: 0.9 }} onClick={loadPrayer}
                    style={{ ...S.iconBtn, marginLeft: 'auto' }}>
                    <RefreshCw size={11} />
                  </motion.button>
                </div>
                {loading.prayer && <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>Loading prayer times…</div>}
                {!loading.prayer && Object.keys(timings).length === 0 && (
                  <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>Prayer times unavailable</div>
                )}
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {Object.entries(timings).filter(([k]) => k !== 'Sunrise').map(([k, v]) => (
                    <div key={k} style={{ background: 'rgba(0,255,200,0.05)', border: '1px solid rgba(0,255,200,0.15)', borderRadius: 6, padding: '6px 8px', minWidth: 62 }}>
                      <div style={{ fontFamily: 'Share Tech Mono', fontSize: 13, color: '#00ffc8' }}>{v}</div>
                      <div style={{ fontSize: 9, color: 'var(--text-dim)' }}>{k}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {districts.map((d, i) => (
                <div key={i} style={S.card}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontFamily: 'Orbitron', fontSize: 11, color: 'var(--cyan)', letterSpacing: 1 }}>{d.name}</span>
                    <span style={{ fontSize: 11, color: 'rgba(0,255,200,0.5)' }}>{d.bn}</span>
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>{d.desc}</div>
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {activeTab === 'news' && (
          <motion.div key="news" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            style={{ display: 'flex', flexDirection: 'column', gap: 8, height: '100%', overflow: 'auto' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 10, color: 'var(--text-dim)', letterSpacing: 1 }}>
                LIVE · {news.length} headlines
              </span>
              <motion.button whileHover={{ scale: 1.1, rotate: 90 }} whileTap={{ scale: 0.9 }} onClick={loadNews}
                style={{ ...S.iconBtn, marginLeft: 'auto' }}>
                <RefreshCw size={11} />
              </motion.button>
            </div>
            {loading.news && <div style={{ padding: 12, textAlign: 'center', color: 'var(--text-dim)', fontSize: 11 }}>Fetching news…</div>}
            {!loading.news && news.length === 0 && (
              <div style={{ padding: 12, textAlign: 'center', color: 'var(--text-dim)', fontSize: 11 }}>
                {error || 'No headlines available right now.'}
              </div>
            )}
            {news.map((item, i) => (
              <a key={i} href={item.link} target="_blank" rel="noreferrer" style={{ textDecoration: 'none' }}>
                <div style={S.card}>
                  <div style={{ fontFamily: 'Rajdhani', fontSize: 14, color: '#e0f0e8', marginBottom: 6, fontWeight: 600 }}>{item.title}</div>
                  {item.summary && (
                    <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 6, lineHeight: 1.4 }}>
                      {item.summary.length > 160 ? `${item.summary.slice(0, 160)}…` : item.summary}
                    </div>
                  )}
                  <div style={{ display: 'flex', gap: 12 }}>
                    <span style={{ fontSize: 10, color: 'rgba(0,255,200,0.6)' }}>{hostOf(item.link)}</span>
                    <span style={{ fontSize: 10, color: 'var(--text-dim)' }}>{verse(item.published)}</span>
                  </div>
                </div>
              </a>
            ))}
          </motion.div>
        )}

        {activeTab === 'economy' && (
          <motion.div key="economy" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            style={{ display: 'flex', flexDirection: 'column', gap: 10, height: '100%', overflow: 'auto' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 10, color: 'var(--text-dim)', letterSpacing: 1 }}>
                {currency ? `FX · 1 UNIT → BDT · ${currency.date || ''}` : 'FX RATES'}
              </span>
              <motion.button whileHover={{ scale: 1.1, rotate: 90 }} whileTap={{ scale: 0.9 }} onClick={loadEconomy}
                style={{ ...S.iconBtn, marginLeft: 'auto' }}>
                <RefreshCw size={11} />
              </motion.button>
            </div>
            {loading.economy && <div style={{ fontSize: 11, color: 'var(--text-dim)' }}>Loading rates…</div>}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 8 }}>
              {currencies.map(([code, rate]) => (
                <div key={code} style={S.card}>
                  <div style={{ fontFamily: 'Orbitron', fontSize: 9, color: 'var(--text-dim)', letterSpacing: 2, marginBottom: 6 }}>{code}</div>
                  <div style={{ fontFamily: 'Share Tech Mono', fontSize: 20, color: '#00aaff' }}>{Number(rate).toFixed(2)}৳</div>
                </div>
              ))}
            </div>
            <div style={{ fontFamily: 'Orbitron', fontSize: 9, color: 'var(--text-dim)', letterSpacing: 2, marginTop: 4 }}>DSE TOP MOVERS</div>
            {stocks.length === 0 && (
              <div style={{ ...S.card, fontSize: 11, color: 'var(--text-dim)' }}>
                {loading.economy ? 'Loading DSE data…' : 'DSE data unavailable right now.'}
              </div>
            )}
            {stocks.map((s, i) => (
              <div key={i} style={{ ...S.card, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontFamily: 'Orbitron', fontSize: 11, color: 'var(--cyan)', letterSpacing: 1 }}>{s.symbol || s.code || s.ticker}</span>
                <div style={{ display: 'flex', gap: 12 }}>
                  <span style={{ fontFamily: 'Share Tech Mono', fontSize: 13, color: '#e0f0e8' }}>{s.price ?? s.ltp ?? '—'}</span>
                  <span style={{ fontFamily: 'Share Tech Mono', fontSize: 12, color: String(s.change || '').includes('-') ? '#ff5533' : '#00ff88' }}>
                    {s.change ?? ''}
                  </span>
                </div>
              </div>
            ))}
          </motion.div>
        )}

        {activeTab === 'divisions' && (
          <motion.div key="divisions" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 8, height: '100%' }}>
            {divisions.map((div, i) => (
              <div key={i} style={S.card}>
                <div style={{ fontFamily: 'Orbitron', fontSize: 10, color: 'var(--cyan)', letterSpacing: 1, marginBottom: 4 }}>{div.name}</div>
                <div style={{ fontSize: 11, color: 'rgba(0,255,200,0.6)' }}>{div.pop}</div>
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

const S = {
  tab: { display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', borderRadius: 8, border: '1px solid', cursor: 'pointer', fontFamily: 'Rajdhani', fontSize: 12, background: 'transparent' },
  card: { background: 'rgba(0,20,16,0.7)', border: '1px solid rgba(0,255,200,0.15)', borderRadius: 10, padding: 12 },
  mainCard: { background: 'rgba(0,20,16,0.7)', border: '1px solid rgba(0,255,200,0.15)', borderRadius: 10, padding: 16, display: 'flex', flexDirection: 'column' },
  iconBtn: { width: 24, height: 24, borderRadius: 6, border: '1px solid rgba(0,255,200,0.2)', background: 'rgba(0,255,200,0.05)', color: 'var(--cyan)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' },
}
