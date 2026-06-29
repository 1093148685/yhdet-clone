import React, { useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

const API_BASE = import.meta.env.VITE_API_BASE || ''
const fallbackAvatar = 'https://yhdet.top/static/avatars/avatar_1.png'
const tokenKey = 'yhdet_token'

function currentRoute() {
  return location.pathname + location.search
}

function navigate(to, { replace = false } = {}) {
  const url = new URL(to, location.origin)
  const next = url.pathname + url.search
  if (url.origin !== location.origin) {
    location.href = url.href
    return
  }
  if (next === currentRoute()) return
  history[replace ? 'replaceState' : 'pushState'](null, '', next)
  window.dispatchEvent(new CustomEvent('app:navigate', { detail: { path: next } }))
}

function useRoute() {
  const [path, setPath] = useState(currentRoute())
  useEffect(() => {
    let raf = 0
    const sync = () => {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
        setPath(currentRoute())
        window.scrollTo({ top: 0, behavior: 'instant' })
      })
    }
    const onClick = e => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return
      const a = e.target.closest('a')
      if (!a || a.target || a.hasAttribute('download')) return
      const url = new URL(a.href, location.origin)
      if (url.origin !== location.origin || url.hash && url.pathname === location.pathname && url.search === location.search) return
      e.preventDefault()
      navigate(url.pathname + url.search)
    }
    window.addEventListener('popstate', sync)
    window.addEventListener('app:navigate', sync)
    document.addEventListener('click', onClick)
    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('popstate', sync)
      window.removeEventListener('app:navigate', sync)
      document.removeEventListener('click', onClick)
    }
  }, [])
  return path
}

let chromeCache = null
let chromePromise = null
function getChrome() {
  if (chromeCache) return Promise.resolve(chromeCache)
  if (!chromePromise) chromePromise = api('/api/chrome').then(d => (chromeCache = d))
  return chromePromise
}

async function api(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) }
  const token = localStorage.getItem(tokenKey)
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  const json = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(json.detail || '请求失败')
  return json
}

function Nav({ me, setMe, path }) {
  const current = new URL(path, location.origin).pathname
  const cls = (path) => `nav-link ${current === path ? 'active' : ''}`
  const logout = () => { localStorage.removeItem(tokenKey); setMe(null); navigate('/') }
  return <nav className="navbar">
    <div className="navbar-inner">
      <a href="/" className="navbar-brand"><span className="logo-icon"><i className="fas fa-comments" /></span>易聊社区</a>
      <div className="navbar-menu">
        <a href="/" className={cls('/')}><i className="fas fa-home" /> 首页</a>
        <a href="/games" className={cls('/games')}><i className="fas fa-gamepad" /> 小游戏</a>
        <a href="/music" className={cls('/music')}><i className="fas fa-music" /> 音乐</a>
        {me?.role === 'admin' && <a href="/admin" className={cls('/admin')}><i className="fas fa-shield-halved" /> 后台</a>}
        {me ? <><a href="/new" className="nav-btn"><i className="fas fa-pen" /> 发帖</a><a href={`/user/${me.id}`} className="nav-link">{me.username}</a><button className="nav-btn nav-btn-outline" onClick={logout}>退出</button></> : <><a href="/login" className="nav-btn nav-btn-outline">登录</a><a href="/register" className="nav-btn">注册</a></>}
      </div>
    </div>
  </nav>
}

function SiteStats({ stats }) {
  return <div className="site-stats" id="siteStats" style={{ textAlign: 'center', padding: '6px 0', fontSize: '0.8rem', color: '#888', background: '#fff', borderBottom: '1px solid #e8e8e8', display: 'block' }}>
    <i className="fas fa-chart-line" style={{ marginRight: 4, color: '#1890ff' }} /> 访问 <span style={{ color: '#1890ff', fontWeight: 600 }}>{stats.visits?.toLocaleString?.() || 0}</span>
    <span style={{ margin: '0 12px', color: '#ddd' }}>|</span>
    <i className="fas fa-users" style={{ marginRight: 4, color: '#52c41a' }} /> 用户 <span style={{ color: '#52c41a', fontWeight: 600 }}>{stats.users}</span>
    <span style={{ margin: '0 12px', color: '#ddd' }}>|</span>
    <i className="fas fa-file-lines" style={{ marginRight: 4, color: '#fa8c16' }} /> 帖子 <span style={{ color: '#fa8c16', fontWeight: 600 }}>{stats.posts}</span>
  </div>
}

function LedBanner({ banners = [] }) {
  const icons = { cyan: '⚡', pink: '🚀', yellow: '🎉', green: '🎮', purple: '🎨' }
  return <div className="led-banner"><div className="led-glow-line" /><div className="led-track" id="ledTrack">
    {[0, 1].map(round => banners.map((b, idx) => <React.Fragment key={`${round}-${idx}`}>{idx > 0 && <div className="led-divider" />}<div className={`led-item ${b.color}`}><span className="led-tag">{b.tag}</span> {icons[b.color] || '✨'} {b.content || b.text}</div></React.Fragment>))}
  </div></div>
}

function PageChrome() {
  const [data, setData] = useState(null)
  useEffect(() => { getChrome().then(setData).catch(() => {}) }, [])
  if (!data) return null
  return <><SiteStats stats={data.stats} /><LedBanner banners={data.banners} /></>
}

function SearchBox({ onSearch }) {
  const [q, setQ] = useState('')
  const [type, setType] = useState('posts')
  return <div className="search-container animate-fadeInUp"><form action="/" method="get" style={{ display: 'flex', gap: 12, width: '100%', flexWrap: 'wrap' }} onSubmit={(e) => { e.preventDefault(); onSearch(q, type) }}>
    <div className="search-input-wrap"><i className="fas fa-search" /><input type="text" name="q" className="search-input" placeholder="搜索帖子或用户..." value={q} onChange={e => setQ(e.target.value)} /></div>
    <select name="type" className="search-select" value={type} onChange={e => setType(e.target.value)}><option value="posts">搜索帖子</option><option value="users">搜索用户</option></select>
    <button type="submit" className="btn btn-primary"><i className="fas fa-search" /> 搜索</button>
  </form></div>
}

function htmlText(s = '') { return s.replace(/<br\s*\/?>/gi, '\n').replace(/<[^>]+>/g, '') }

function PostItem({ post }) {
  return <a href={`/post/${post.id}`} className="post-item" style={{ textDecoration: 'none', display: 'block' }} onMouseDown={e => e.currentTarget.classList.add('is-active')} onBlur={e => e.currentTarget.classList.remove('is-active')}>
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
      <img src={post.avatar || fallbackAvatar} alt="" className="post-avatar" loading="lazy" decoding="async" onError={e => { e.currentTarget.src = fallbackAvatar }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="post-title">{post.title}</div>
        <div className="post-preview">{htmlText(post.preview || post.content)}</div>
        <div className="post-meta"><div className="post-meta-item"><a href={`/user/${post.user_id}`} className="post-author-name" onClick={e => e.stopPropagation()}>{post.author}</a>{post.role && <span className="role-badge role-super-admin"><i className="fas fa-crown" /> {post.role}</span>}</div><div className="post-meta-item"><i className="far fa-clock" /> {post.time}</div><div className="post-stats"><span className="post-stat"><i className="far fa-comment" /> {post.comments || ''}</span><span className="post-stat"><i className="far fa-eye" /> {post.views || ''}</span></div></div>
        {post.custom_title && <span className="custom-title" style={{ marginTop: 6 }}>{post.custom_title}</span>}
      </div>
    </div>
  </a>
}

function Sidebar({ donors = [], notice = {} }) {
  return <div><div className="card sidebar-card animate-fadeInUp" style={{ animationDelay: '0.1s' }}><div className="card-header"><h3><i className="fas fa-heart" style={{ color: '#FF6584' }} /> 捐赠者</h3></div><div className="card-body">{donors.map(d => <div className="donor-item" key={d.name}><div className="donor-icon"><i className="fas fa-star" /></div><div style={{ flex: 1, minWidth: 0 }}><div style={{ fontWeight: 500, fontSize: '0.9rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{d.name}</div><div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{d.amount} · {d.date}</div></div></div>)}</div></div>
  <div className="card sidebar-card animate-fadeInUp" style={{ animationDelay: '0.2s' }}><div className="card-header"><h3><i className="fas fa-bullhorn" style={{ color: 'var(--primary)' }} /> 公告</h3></div><div className="card-body"><div style={{ padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}><div style={{ fontSize: '0.85rem', color: '#333', lineHeight: 1.5, wordBreak: 'break-all' }}>{notice.text}</div><div style={{ fontSize: '0.75rem', color: '#999', marginTop: 4 }}>{notice.author} · {notice.time}</div></div></div></div></div>
}

function UserResults({ users }) {
  return <div className="card animate-fadeInUp"><div className="card-header"><h3><i className="fas fa-users" /> 用户搜索结果</h3></div><div className="card-body"><div className="user-grid">{users.length ? users.map(u => <a className="user-card" href={`/user/${u.id}`} key={u.id} style={{ textDecoration: 'none' }}><img className="user-card-avatar" loading="lazy" decoding="async" src={u.avatar || fallbackAvatar} onError={e => { e.currentTarget.src = fallbackAvatar }} /><div className="user-card-name">{u.username}</div><div className="user-card-bio">{u.role_label || '社区用户'}</div></a>) : <div className="empty-state"><i className="fas fa-search" /><p>没有找到用户</p></div>}</div></div></div>
}

function Home() {
  const [data, setData] = useState(null)
  const [posts, setPosts] = useState([])
  const [users, setUsers] = useState(null)
  useEffect(() => { api('/api/home').then(d => { setData(d); setPosts(d.posts) }) }, [])
  async function onSearch(q, type) { const res = await api(`/api/search?q=${encodeURIComponent(q)}&type=${type}`); if (type === 'users') setUsers(res.items); else { setUsers(null); setPosts(res.items) } }
  if (!data) return <Loading />
  return <><SiteStats stats={data.stats} /><LedBanner banners={data.banners} /><div className="main-content"><SearchBox onSearch={onSearch} /><div className="home-layout"><div>{users ? <UserResults users={users} /> : <div className="card animate-fadeInUp"><div className="card-header"><h3><i className="fas fa-fire" style={{ color: 'var(--secondary)' }} /> 最新帖子</h3></div><div>{posts.length ? posts.map(p => <PostItem key={p.id} post={p} />) : <div className="empty-state"><i className="fas fa-search" /><p>没有找到帖子</p></div>}</div></div>}</div><Sidebar donors={data.donors} notice={data.notice} /></div></div></>
}

function CaptchaBox({ value, onChange }) {
  const [code, setCode] = useState('')
  const canvasRef = React.useRef(null)
  const gen = () => setCode(Math.random().toString(36).toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 5).padEnd(5, '8'))
  useEffect(gen, [])
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    canvas.width = 120; canvas.height = 40
    ctx.fillStyle = '#f5f5f5'; ctx.fillRect(0, 0, 120, 40)
    for (let i = 0; i < 3; i++) {
      ctx.beginPath(); ctx.moveTo(Math.random() * 120, Math.random() * 40); ctx.lineTo(Math.random() * 120, Math.random() * 40)
      ctx.strokeStyle = '#ddd'; ctx.lineWidth = 1; ctx.stroke()
    }
    for (let i = 0; i < code.length; i++) {
      ctx.save(); ctx.translate(16 + i * 22, 26 + (Math.random() - 0.5) * 6); ctx.rotate((Math.random() - 0.5) * 0.4)
      ctx.font = 'bold 18px sans-serif'; ctx.fillStyle = '#666'; ctx.fillText(code[i], 0, 0); ctx.restore()
    }
  }, [code])
  return <div className="form-group">
    <label className="form-label">验证码</label>
    <div className="captcha-container">
      <input type="text" className="form-input captcha-input" placeholder="请输入验证码" required maxLength={5} value={value} onChange={e => onChange(e.target.value)} />
      <canvas ref={canvasRef} className="captcha-canvas" onClick={gen} title="点击刷新验证码" />
    </div>
    <p className="captcha-hint">点击图片刷新</p>
  </div>
}

function AuthPage({ mode, setMe }) {
  const isLogin = mode === 'login'
  useEffect(() => { document.title = `${isLogin ? '登录' : '注册'} - 易聊社区` }, [isLogin])
  const [form, setForm] = useState({ username: '', email: '', email_code: '', password: '', captcha: '' })
  const [err, setErr] = useState('')
  const [hint, setHint] = useState('')
  const [hintColor, setHintColor] = useState('#aaa')
  const [loading, setLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const [countdown, setCountdown] = useState(0)
  useEffect(() => {
    if (!countdown) return
    const t = setInterval(() => setCountdown(v => v <= 1 ? 0 : v - 1), 1000)
    return () => clearInterval(t)
  }, [countdown])
  async function sendEmailCode() {
    if (!form.email.trim()) { setHintColor('#b91c1c'); setHint('请先输入邮箱地址'); return }
    setSending(true); setHintColor('#666'); setHint('正在发送...')
    try {
      const res = await api('/api/send_email_code', { method: 'POST', body: JSON.stringify({ email: form.email.trim() }) })
      setHintColor(res.success ? '#16a34a' : '#b91c1c'); setHint(res.message || (res.success ? '验证码已发送，请查收邮箱' : '发送失败'))
      if (res.success) setCountdown(60)
    } catch (e) { setHintColor('#b91c1c'); setHint(e.message || '网络错误，请重试') }
    finally { setSending(false) }
  }
  async function submit(e) {
    e.preventDefault(); setErr('')
    if (!form.username.trim() || !form.password.trim()) return setErr('请填写用户名和密码')
    if (!form.captcha.trim()) return setErr('请填写验证码')
    if (!isLogin && !form.email.trim()) return setErr('请填写邮箱')
    setLoading(true)
    try {
      const payload = { ...form, username: form.username.trim(), email: form.email.trim() || null }
      const res = await api(isLogin ? '/api/login' : '/api/register', { method: 'POST', body: JSON.stringify(payload) })
      localStorage.setItem(tokenKey, res.token); setMe(res.user); navigate('/')
    } catch (e) { setErr(e.message) } finally { setLoading(false) }
  }
  return <div className="auth-page">
    <div className={isLogin ? 'login-card' : 'register-card'}>
      <div className={isLogin ? 'login-header' : 'register-header'}><h1>{isLogin ? '登录' : '注册'}</h1><p>易聊社区</p></div>
      {err && <div className="alert alert-error">{err}</div>}
      <form onSubmit={submit}>
        <div className="form-group"><label className="form-label" htmlFor="username">用户名</label><input id="username" type="text" className="form-input" placeholder="请输入用户名" required value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} /></div>
        {!isLogin && <div className="form-group"><label className="form-label" htmlFor="email">邮箱</label><input id="email" type="text" className="form-input" placeholder="请输入邮箱地址" required value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} /><p className="form-hint">没有邮箱？填 手机号@phoneTEL（如：13812345678@phoneTEL）</p></div>}
        {!isLogin && <div className="form-group"><label className="form-label">邮箱验证码</label><div style={{ display: 'flex', gap: 10 }}><input type="text" className="form-input" placeholder="请输入6位邮箱验证码" required maxLength={6} style={{ flex: 1 }} value={form.email_code} onChange={e => setForm({ ...form, email_code: e.target.value })} /><button type="button" className="btn btn-primary send-code-btn" disabled={sending || countdown > 0} onClick={sendEmailCode}>{sending ? '发送中...' : countdown > 0 ? `${countdown}s后重发` : '发送验证码'}</button></div><p className="form-hint" style={{ color: hintColor }}>{hint}</p></div>}
        <div className="form-group"><label className="form-label" htmlFor="password">密码</label><input id="password" type="password" className="form-input" placeholder="请输入密码" required minLength={4} value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} /></div>
        <CaptchaBox value={form.captcha} onChange={captcha => setForm({ ...form, captcha })} />
        <button type="submit" className="btn btn-primary auth-submit" disabled={loading}>{loading ? '提交中...' : (isLogin ? '登录' : '注册')}</button>
      </form>
      <div className={isLogin ? 'login-footer' : 'register-footer'}>{isLogin ? <>没有账号？<a href="/register">立即注册</a></> : <>已有账号？<a href="/login">立即登录</a></>}</div>
    </div>
    <div className="sticker"><img src="/static/sticker.png" alt="" loading="lazy" decoding="async" onError={e => { e.currentTarget.style.display = 'none' }} /></div>
  </div>
}

function NewPost({ me }) {
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [err, setErr] = useState('')
  if (!me) return <div className="main-content"><div className="alert alert-info"><i className="fas fa-info-circle" /> 请先 <a href="/login">登录</a> 后发帖</div></div>
  async function submit(e) { e.preventDefault(); setErr(''); if (!title.trim() || !content.trim()) return setErr('标题和内容不能为空'); try { const res = await api('/api/posts', { method: 'POST', body: JSON.stringify({ title: title.trim(), content: content.trim() }) }); navigate(`/post/${res.id}`) } catch (e) { setErr(e.message) } }
  return <div className="main-content"><div className="card"><div className="card-header"><h3><i className="fas fa-pen" /> 发布帖子</h3></div><div className="card-body">{err && <div className="alert alert-error">{err}</div>}<form onSubmit={submit}><div className="form-group"><label className="form-label">标题</label><input className="form-input" required maxLength={120} value={title} onChange={e => setTitle(e.target.value)} placeholder="请输入标题" /></div><div className="form-group"><label className="form-label">内容</label><textarea className="form-textarea" required maxLength={10000} value={content} onChange={e => setContent(e.target.value)} placeholder="请输入内容" style={{ minHeight: 220 }} /></div><button className="btn btn-primary"><i className="fas fa-paper-plane" /> 发布</button></form></div></div></div>
}

function renderContent(content = '') {
  return htmlText(content).split(/\n{2,}/).map((para, idx) => <p key={idx}>{para}</p>)
}

function PostDetail({ id, me }) {
  const [data, setData] = useState(null)
  const [content, setContent] = useState('')
  const [err, setErr] = useState('')
  const load = () => api(`/api/posts/${id}`).then(d => { setData(d); document.title = `${d.post.title} - 易聊社区` }).catch(e => setErr(e.message))
  useEffect(load, [id])
  async function comment(e) { e.preventDefault(); setErr(''); if (!content.trim()) return setErr('评论内容不能为空'); try { await api(`/api/posts/${id}/comments`, { method: 'POST', body: JSON.stringify({ content: content.trim() }) }); setContent(''); load() } catch (e) { setErr(e.message) } }
  if (err && !data) return <><PageChrome /><div className="main-content"><div className="alert alert-error">{err}</div></div></>
  if (!data) return <Loading />
  const p = data.post
  return <><PageChrome /><div className="main-content"><div className="detail-wrap">
    <div className="card animate-fadeInUp post-detail-card">
      <div className="card-header post-detail-header">
        <h2>{p.title}</h2>
        <div className="post-meta detail-meta">
          <div className="post-author">
            <img className="post-avatar" loading="lazy" decoding="async" src={p.avatar || fallbackAvatar} alt="头像" onError={e => e.currentTarget.src = fallbackAvatar} />
            <a className="post-author-name" href={`/user/${p.user_id}`}>{p.author}</a>
            {p.role ? <span className="role-badge role-super-admin"><i className="fas fa-crown" /> {p.role.includes('超级') ? p.role : p.role === '超管' ? '超级管理员' : p.role}</span> : <span className="role-badge role-user"><i className="fas fa-user" /> 用户</span>}
          </div>
          {p.custom_title && <span className="custom-title">{p.custom_title}</span>}
          <div className="post-meta-item"><i className="far fa-clock" /> {p.time}</div>
          <div className="post-meta-item detail-counts"><i className="far fa-comment" /> {data.comments.length || ''}<span className="meta-split">|</span><i className="far fa-eye" /> {p.views || ''}</div>
        </div>
      </div>
      <div className="card-body"><div className="markdown-body">{renderContent(p.content)}</div></div>
    </div>

    <div className="card animate-fadeInUp reply-card" style={{ animationDelay: '0.1s' }}>
      <div className="card-header"><h3><i className="fas fa-comments" style={{ color: 'var(--primary)' }} /> 回复 ({data.comments.length})</h3></div>
      <div>{data.comments.length ? data.comments.map(c => <div className="post-item reply-item" key={c.id} tabIndex={0}><div className="reply-row"><img className="post-avatar" loading="lazy" decoding="async" src={c.avatar || fallbackAvatar} alt="头像" onError={e => e.currentTarget.src = fallbackAvatar} /><div className="reply-main"><div className="reply-head"><a className="post-author-name" href={`/user/${c.user_id || ''}`}>{c.author}</a><span><i className="far fa-clock" /> {c.time}</span></div><div className="markdown-body reply-content"><p>{c.content}</p></div></div></div></div>) : <div className="empty-state"><i className="fas fa-comment-dots" /><p>暂无回复，来说点什么吧</p></div>}</div>
    </div>

    <div className="card animate-fadeInUp" style={{ animationDelay: '0.2s' }}>
      <div className="card-body reply-form-body">{err && <div className="alert alert-error">{err}</div>}{me ? <form onSubmit={comment}><textarea className="form-textarea" required maxLength={2000} value={content} onChange={e => setContent(e.target.value)} placeholder="写下你的回复" /><button className="btn btn-primary" style={{ marginTop: 10 }}><i className="fas fa-paper-plane" /> 发表回复</button></form> : <><p>登录后即可发表回复</p><a className="btn btn-primary" href="/login"><i className="fas fa-right-to-bracket" /> 去登录</a></>}</div>
    </div>

    <div className="back-home"><a className="btn btn-secondary" href="/"><i className="fas fa-arrow-left" /> 返回首页</a></div>
  </div></div></>
}

function UserPage({ id }) {
  const [data, setData] = useState(null)
  useEffect(() => { api(`/api/users/${id}`).then(d => { setData(d); document.title = `${d.user.username} 的主页 - 易聊社区` }) }, [id])
  if (!data) return <Loading />
  const u = data.user
  return <><PageChrome /><div className="main-content"><div className="detail-wrap">
    <div className="card animate-fadeInUp user-profile-card">
      <div className="card-body user-profile-body"><img className="profile-avatar" loading="lazy" decoding="async" src={u.avatar || fallbackAvatar} alt="头像" onError={e => e.currentTarget.src = fallbackAvatar} /><h2>{u.username}</h2><div className="profile-badges">{u.role_label ? <span className="role-badge role-super-admin"><i className="fas fa-crown" /> {u.role_label}</span> : <span className="role-badge role-user"><i className="fas fa-user" /> 用户</span>}{u.custom_title && <span className="custom-title">{u.custom_title}</span>}</div></div>
    </div>
    <div className="card animate-fadeInUp" style={{ animationDelay: '0.1s' }}><div className="card-header"><h3><i className="fas fa-pen-nib" style={{ color: 'var(--primary)' }} /> TA 的帖子</h3></div><div>{data.posts.length ? data.posts.map(p => <PostItem key={p.id} post={p} />) : <div className="empty-state"><i className="fas fa-feather-pointed" /><p>TA 还没有发表过帖子</p></div>}</div></div>
    <div className="back-home"><a className="btn btn-secondary" href="/"><i className="fas fa-arrow-left" /> 返回首页</a></div>
  </div></div></>
}

function SimpleSection({ type }) {
  const [data, setData] = useState(null)
  useEffect(() => { document.title = `${type === 'games' ? '小游戏' : '音乐'} - 易聊社区`; api(`/api/${type}`).then(setData) }, [type])
  return <div className="main-content"><div className="card"><div className="card-header"><h3><i className={`fas ${type === 'games' ? 'fa-gamepad' : 'fa-music'}`} /> {type === 'games' ? '小游戏' : '音乐'}</h3></div><div className="card-body"><div className="alert alert-info">{data?.message || '加载中...'}</div><div className="user-grid">{data?.items?.map(x => <div className="user-card" key={x}><div className="empty-state" style={{ padding: 10 }}><i className={`fas ${type === 'games' ? 'fa-gamepad' : 'fa-music'}`} /><p>{x}</p></div></div>)}</div></div></div></div>
}


function AdminPage({ me }) {
  const tabs = [
    ['overview', '总览', 'fa-chart-line'],
    ['posts', '帖子', 'fa-file-lines'],
    ['comments', '评论', 'fa-comments'],
    ['users', '用户', 'fa-users'],
    ['announcements', '公告', 'fa-bullhorn'],
    ['donors', '捐赠者', 'fa-heart'],
  ]
  const [tab, setTab] = useState('overview')
  const [data, setData] = useState({})
  const [q, setQ] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const [draft, setDraft] = useState({})
  useEffect(() => { document.title = '管理后台 - 易聊社区' }, [])
  useEffect(() => { if (me?.role === 'admin') load(tab) }, [tab, me])
  if (!me) return <div className="main-content"><div className="alert alert-info">请先 <a href="/login">登录</a> 后进入后台</div></div>
  if (me.role !== 'admin') return <div className="main-content"><div className="alert alert-error">当前账号不是管理员，无法访问后台</div></div>
  async function load(nextTab = tab, query = q) {
    setErr(''); setBusy(true)
    try {
      const url = ['/posts', '/comments', '/users'].some(x => `/api/admin/${nextTab}`.endsWith(x)) ? `/api/admin/${nextTab}?q=${encodeURIComponent(query)}` : `/api/admin/${nextTab}`
      const res = await api(url)
      setData(d => ({ ...d, [nextTab]: res }))
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }
  async function run(fn) {
    setErr(''); setBusy(true)
    try { await fn(); await load(tab); chromeCache = null; chromePromise = null }
    catch (e) { setErr(e.message) }
    finally { setBusy(false) }
  }
  const items = data[tab]?.items || []
  return <div className="admin-page">
    <div className="admin-hero">
      <div><h1><i className="fas fa-shield-halved" /> 管理后台</h1><p>内容、用户、公告和捐赠记录统一管理</p></div>
      <a className="btn btn-secondary" href="/"><i className="fas fa-arrow-left" /> 返回前台</a>
    </div>
    <div className="admin-tabs">{tabs.map(t => <button key={t[0]} className={`admin-tab ${tab === t[0] ? 'active' : ''}`} onClick={() => { setTab(t[0]); setQ('') }}><i className={`fas ${t[2]}`} /> {t[1]}</button>)}</div>
    {err && <div className="alert alert-error">{err}</div>}
    {busy && <div className="admin-busy">正在处理...</div>}
    {tab === 'overview' && <AdminOverview data={data.overview} />}
    {['posts', 'comments', 'users'].includes(tab) && <div className="admin-toolbar"><input className="form-input" placeholder="搜索标题、用户或内容" value={q} onChange={e => setQ(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') load(tab, q) }} /><button className="btn btn-primary" onClick={() => load(tab, q)}><i className="fas fa-search" /> 搜索</button></div>}
    {tab === 'posts' && <AdminPosts items={items} run={run} />}
    {tab === 'comments' && <AdminComments items={items} run={run} />}
    {tab === 'users' && <AdminUsers items={items} run={run} />}
    {tab === 'announcements' && <AdminAnnouncements items={items} draft={draft} setDraft={setDraft} run={run} />}
    {tab === 'donors' && <AdminDonors items={items} draft={draft} setDraft={setDraft} run={run} />}
  </div>
}

function AdminOverview({ data }) {
  const stats = data?.stats || {}
  return <><div className="admin-stat-grid">
    <div className="admin-stat"><span>访问</span><b>{stats.visits || 0}</b></div><div className="admin-stat"><span>用户</span><b>{stats.users || 0}</b></div><div className="admin-stat"><span>帖子</span><b>{stats.posts || 0}</b></div><div className="admin-stat"><span>评论</span><b>{stats.comments || 0}</b></div>
  </div><div className="admin-grid"><div className="admin-card"><h3>最新帖子</h3>{data?.recent_posts?.map(p => <div className="admin-line" key={p.id}><span>{p.title}</span><a href={`/post/${p.id}`}>查看</a></div>)}</div><div className="admin-card"><h3>新用户</h3>{data?.recent_users?.map(u => <div className="admin-line" key={u.id}><span>{u.username}</span><span>{u.role === 'admin' ? '管理员' : '用户'}</span></div>)}</div></div></>
}
function AdminPosts({ items, run }) { return <div className="admin-card"><h3>帖子管理</h3>{items.map(p => <div className="admin-row" key={p.id}><div><b>{p.title}</b><p>{p.author} · {p.time} · 评论 {p.comments || 0} · 浏览 {p.views || 0}</p></div><div className="admin-actions"><button className="btn btn-sm btn-secondary" onClick={() => run(() => api(`/api/admin/posts/${p.id}`, { method:'PATCH', body: JSON.stringify({ pinned: !p.pinned }) }))}>{p.pinned ? '取消置顶' : '置顶'}</button><a className="btn btn-sm btn-secondary" href={`/post/${p.id}`}>查看</a><button className="btn btn-sm btn-danger" onClick={() => confirm('确定删除这个帖子及其评论？') && run(() => api(`/api/admin/posts/${p.id}`, { method:'DELETE' }))}>删除</button></div></div>)}</div> }
function AdminComments({ items, run }) { return <div className="admin-card"><h3>评论管理</h3>{items.map(c => <div className="admin-row" key={c.id}><div><b>{c.author}</b><p>{c.content}</p><small>来自《{c.post_title}》 · {c.created_at}</small></div><div className="admin-actions"><a className="btn btn-sm btn-secondary" href={`/post/${c.post_id}`}>查看帖子</a><button className="btn btn-sm btn-danger" onClick={() => confirm('确定删除这条评论？') && run(() => api(`/api/admin/comments/${c.id}`, { method:'DELETE' }))}>删除</button></div></div>)}</div> }
function AdminUsers({ items, run }) { return <div className="admin-card"><h3>用户管理</h3>{items.map(u => <div className="admin-row" key={u.id}><div><b>{u.username}</b><p>{u.role === 'admin' ? '管理员' : '普通用户'} · 帖子 {u.post_count || 0} · 评论 {u.comment_count || 0}</p><small>{u.role_label || '无头衔'} {u.custom_title ? ` · ${u.custom_title}` : ''}</small></div><div className="admin-actions"><button className="btn btn-sm btn-secondary" onClick={() => run(() => api(`/api/admin/users/${u.id}`, { method:'PATCH', body: JSON.stringify({ role: u.role === 'admin' ? 'user' : 'admin', role_label: u.role === 'admin' ? '' : '超管', custom_title: u.role === 'admin' ? '' : '论坛主' }) }))}>{u.role === 'admin' ? '降为用户' : '设为管理员'}</button><a className="btn btn-sm btn-secondary" href={`/user/${u.id}`}>主页</a></div></div>)}</div> }
function AdminAnnouncements({ items, draft, setDraft, run }) { return <div className="admin-card"><h3>公告管理</h3><div className="admin-create"><input className="form-input" placeholder="新公告内容" value={draft.announcement || ''} onChange={e => setDraft({ ...draft, announcement: e.target.value })} /><button className="btn btn-primary" onClick={() => draft.announcement?.trim() && run(() => api('/api/admin/announcements', { method:'POST', body: JSON.stringify({ content: draft.announcement.trim() }) }).then(() => setDraft({ ...draft, announcement: '' })))}>发布公告</button></div>{items.map(a => <div className="admin-row" key={a.id}><div><b>{a.content}</b><p>{a.author} · {a.created_at}</p></div><button className="btn btn-sm btn-danger" onClick={() => confirm('确定删除公告？') && run(() => api(`/api/admin/announcements/${a.id}`, { method:'DELETE' }))}>删除</button></div>)}</div> }
function AdminDonors({ items, draft, setDraft, run }) { const d = draft.donor || {}; return <div className="admin-card"><h3>捐赠者管理</h3><div className="admin-create donor-create"><input className="form-input" placeholder="名称" value={d.name || ''} onChange={e => setDraft({ ...draft, donor: { ...d, name: e.target.value } })} /><input className="form-input" placeholder="金额，如 3元" value={d.amount || ''} onChange={e => setDraft({ ...draft, donor: { ...d, amount: e.target.value } })} /><input className="form-input" placeholder="日期，如 2026.6.29" value={d.donated_at || ''} onChange={e => setDraft({ ...draft, donor: { ...d, donated_at: e.target.value } })} /><button className="btn btn-primary" onClick={() => d.name?.trim() && d.amount?.trim() && d.donated_at?.trim() && run(() => api('/api/admin/donors', { method:'POST', body: JSON.stringify({ name: d.name.trim(), amount: d.amount.trim(), donated_at: d.donated_at.trim() }) }).then(() => setDraft({ ...draft, donor: {} })))}>添加</button></div>{items.map(x => <div className="admin-row" key={x.id}><div><b>{x.name}</b><p>{x.amount} · {x.donated_at}</p></div><button className="btn btn-sm btn-danger" onClick={() => confirm('确定删除捐赠记录？') && run(() => api(`/api/admin/donors/${x.id}`, { method:'DELETE' }))}>删除</button></div>)}</div> }

function Loading() { return <div className="page-loading"><div className="loading-card"><span className="loading-dot" /> 正在加载...</div></div> }

function App() {
  const path = useRoute()
  const [me, setMe] = useState(null)
  useEffect(() => { api('/api/me').then(r => setMe(r.user)).catch(() => {}) }, [])
  const page = useMemo(() => {
    const pathname = new URL(path, location.origin).pathname
    if (pathname === '/login') return <AuthPage mode="login" setMe={setMe} />
    if (pathname === '/register') return <AuthPage mode="register" setMe={setMe} />
    if (pathname === '/new') return <NewPost me={me} />
    if (pathname === '/admin') return <AdminPage me={me} />
    if (pathname.startsWith('/post/')) return <PostDetail id={pathname.split('/')[2]} me={me} />
    if (pathname.startsWith('/user/')) return <UserPage id={pathname.split('/')[2]} />
    if (pathname === '/games') return <SimpleSection type="games" />
    if (pathname === '/music') return <SimpleSection type="music" />
    return <Home />
  }, [path, me])
  const isAuth = new URL(path, location.origin).pathname === '/login' || new URL(path, location.origin).pathname === '/register'
  return isAuth ? page : <><Nav me={me} setMe={setMe} path={path} />{page}<footer className="footer"><p>易聊社区</p></footer></>
}

createRoot(document.getElementById('root')).render(<App />)
