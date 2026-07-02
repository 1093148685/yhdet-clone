import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { createPortal } from 'react-dom'
import './styles.css'

const API_BASE = import.meta.env.VITE_API_BASE || ''
const fallbackAvatar = '/static/avatar.svg'
const tokenKey = 'yhdet_token'
const avatarFallbacks = ['/static/avatar.svg']
const defaultSite = { site_name: '泓聊社区', site_logo: '', default_avatar: fallbackAvatar }

function absoluteUrl(path = '/') {
  try { return new URL(path, location.origin).href } catch { return location.origin + '/' }
}
function setMetaAttr(selector, attr, value) {
  let el = document.head.querySelector(selector)
  if (!el) {
    el = document.createElement('meta')
    const name = selector.match(/meta\[(name|property)="([^"]+)"\]/)
    if (name) el.setAttribute(name[1], name[2])
    document.head.appendChild(el)
  }
  el.setAttribute(attr, value || '')
}
function updateSeo({ title = '泓聊社区 - 首页', description = '泓聊社区，轻量实时社区，浏览帖子、评论互动、兑换社区权益。', url = absoluteUrl(location.pathname), image = absoluteUrl('/favicon.svg'), type = 'website' } = {}) {
  document.title = title
  setMetaAttr('meta[name="description"]', 'content', description)
  setMetaAttr('meta[property="og:title"]', 'content', title)
  setMetaAttr('meta[property="og:description"]', 'content', description)
  setMetaAttr('meta[property="og:url"]', 'content', url)
  setMetaAttr('meta[property="og:image"]', 'content', image)
  setMetaAttr('meta[property="og:type"]', 'content', type)
  setMetaAttr('meta[name="twitter:card"]', 'content', 'summary')
}
function textExcerpt(text = '', limit = 150) {
  const clean = htmlText(String(text || '')).replace(/[#*_`>\[\]()]/g, ' ').replace(/\s+/g, ' ').trim()
  return clean.slice(0, limit)
}
async function copyText(text, success = '链接已复制') {
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    const ta = document.createElement('textarea')
    ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0'; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); ta.remove()
  }
  notify(success, 'success')
}
function sortCommentsForDisplay(comments = []) {
  if (comments.some(c => Number(c.comment_rank_score || 0) > 0)) {
    return [...comments].sort((a, b) => Number(b.comment_rank_score || 0) - Number(a.comment_rank_score || 0) || Number(b.id || 0) - Number(a.id || 0))
  }
  const nowTs = Date.now()
  const replyCounts = new Map()
  for (const c of comments) if (c.reply_to_comment_id) replyCounts.set(Number(c.reply_to_comment_id), (replyCounts.get(Number(c.reply_to_comment_id)) || 0) + 1)
  return [...comments].sort((a, b) => {
    const at = new Date(a.time || a.created_at || 0).getTime() || 0
    const bt = new Date(b.time || b.created_at || 0).getTime() || 0
    const afresh = nowTs - at < 60000
    const bfresh = nowTs - bt < 60000
    if (afresh !== bfresh) return afresh ? -1 : 1
    if (afresh && bfresh) return bt - at
    const ar = replyCounts.get(Number(a.id)) || 0
    const br = replyCounts.get(Number(b.id)) || 0
    if (ar !== br) return br - ar
    return bt - at || Number(b.id || 0) - Number(a.id || 0)
  })
}
function safeAvatar(src) {
  if (!src || typeof src !== 'string') return avatarFallbacks[0]
  if (src.includes('robots.txt') || src.includes('t.alcy.cc')) return avatarFallbacks[0]
  return src
}
function onAvatarError(e) {
  const img = e.currentTarget
  const idx = Number(img.dataset.fallbackIndex || 0)
  if (idx < avatarFallbacks.length) {
    img.dataset.fallbackIndex = String(idx + 1)
    img.src = avatarFallbacks[idx]
  } else {
    img.style.display = 'none'
  }
}
function normalizeAvatarBorderStyle(style = '') {
  return String(style || '').trim()
}
function hasAvatarPrivilegeBorder(user) {
  const s = normalizeAvatarBorderStyle(user?.avatar_border_style).toLowerCase()
  return Boolean(s && s !== '#fff' && s !== '#ffffff' && s !== 'white' && s !== 'transparent' && s !== 'rgba(0,0,0,0)' && s !== 'rgba(0, 0, 0, 0)')
}
function avatarBorderStyle(user) { return hasAvatarPrivilegeBorder(user) ? normalizeAvatarBorderStyle(user?.avatar_border_style) : 'transparent' }
function AvatarRing({ user, src, alt = '头像', size = 48, className = '', imgClassName = '', href = '', title = '' }) {
  let liveUser = user || {}
  try {
    const current = JSON.parse(localStorage.getItem('yhdet_user') || '{}')
    if (current?.id && liveUser?.id && String(current.id) === String(liveUser.id)) liveUser = { ...liveUser, ...current }
  } catch {}
  const image = safeAvatar(src || liveUser?.avatar)
  const privileged = hasAvatarPrivilegeBorder(liveUser)
  const ringStyle = { width:size, height:size, padding: privileged ? 1.5 : 0, background: privileged ? avatarBorderStyle(liveUser) : 'transparent' }
  const ring = <div className={`avatar-ring ${privileged ? 'has-privilege-ring' : 'no-privilege-ring'} ${className}`} style={ringStyle} title={title || liveUser?.username || alt}>
    <img src={image} alt={alt} className={`avatar-ring-img ${privileged ? 'has-privilege-img' : 'no-privilege-img'} ${imgClassName}`} loading="lazy" decoding="async" onError={onAvatarError} />
  </div>
  return href ? <a href={href} className="avatar-ring-link">{ring}</a> : ring
}
function usernameClass(obj) { return obj?.display_flags?.red_username ? 'username-red' : '' }
function UsernameBadge({ user }) { return user?.username_badge ? <span className="username-badge" aria-label="昵称图标">{user.username_badge}</span> : null }
function profileThemeClass(user) { return user?.profile_theme ? `profile-theme-${String(user.profile_theme).replace(/[^a-z0-9_-]/gi, '')}` : '' }
function commentThemeClass(user) { return user?.comment_theme ? `comment-theme-${String(user.comment_theme).replace(/[^a-z0-9_-]/gi, '')}` : '' }
function isInstantDressupItem(item = {}) {
  try {
    const effect = JSON.parse(item.payload_json || '{}')?.effect
    return ['avatar_border_style','username_badge','custom_title','profile_theme','comment_theme'].includes(effect)
  } catch { return isAvatarBorderItem(item) }
}

function currentRoute() {
  return location.pathname + location.search
}

function navigate(to, { replace = false } = {}) {
  const url = new URL(to, location.origin)
  const next = url.pathname + url.search
  const from = currentRoute()
  if (url.origin !== location.origin) {
    location.href = url.href
    return
  }
  if (next === from) return
  history[replace ? 'replaceState' : 'pushState'](null, '', next)
  window.dispatchEvent(new CustomEvent('app:navigate', { detail: { path: next, from } }))
}

function useRoute() {
  const [path, setPath] = useState(currentRoute())
  useEffect(() => {
    if ('scrollRestoration' in history) history.scrollRestoration = 'manual'
    let raf = 0
    const sync = (event) => {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
        const next = currentRoute()
        const prev = event?.detail?.from || document.documentElement.dataset.route || ''
        setPath(next)
        document.documentElement.dataset.route = next
        const nextPath = new URL(next, location.origin).pathname
        const prevPath = new URL(prev || '/', location.origin).pathname
        const returningHomeFromPost = nextPath === '/' && prevPath.startsWith('/post/')
        if (!returningHomeFromPost) window.scrollTo({ top: 0, behavior: 'auto' })
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
let homeStateCache = null
function syncStoredUser(user) {
  if (!user) return null
  localStorage.setItem('yhdet_user', JSON.stringify(user))
  window.dispatchEvent(new CustomEvent('app:user-updated', { detail: user }))
  return user
}
function mergeStoredUser(patch = {}) {
  const current = JSON.parse(localStorage.getItem('yhdet_user') || '{}')
  return syncStoredUser({ ...current, ...patch })
}
function getChrome() {
  if (chromeCache) return Promise.resolve(chromeCache)
  if (!chromePromise) chromePromise = api('/api/chrome').then(d => (chromeCache = d))
  return chromePromise
}

async function api(path, options = {}) {
  const isForm = options.body instanceof FormData
  const headers = { ...(isForm ? {} : { 'Content-Type': 'application/json' }), ...(options.headers || {}) }
  const token = localStorage.getItem(tokenKey)
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  const json = await res.json().catch(() => ({}))
  if (!res.ok) {
    if (res.status === 403 && /冻结|封禁|禁止访问/.test(json.detail || '')) {
      localStorage.removeItem(tokenKey)
      localStorage.removeItem('yhdet_user')
      window.dispatchEvent(new CustomEvent('app:session-expired', { detail: json.detail || '账号不可用' }))
    }
    throw new Error(json.detail || '请求失败')
  }
  return json
}

function Nav({ me, setMe, path, site = defaultSite }) {
  const current = new URL(path, location.origin).pathname
  const cls = (path) => `nav-link ${current === path ? 'active' : ''}`
  const logout = () => { localStorage.removeItem(tokenKey); localStorage.removeItem('yhdet_user'); setMe(null); navigate('/') }
  return <nav className="navbar">
    <div className="navbar-inner">
      <a href="/" className="navbar-brand"><span className="logo-icon">{site.site_logo ? <img src={safeAvatar(site.site_logo)} alt="" /> : <i className="fas fa-comments" />}</span>{site.site_name || '泓聊社区'}</a>
      <div className="navbar-menu">
        <a href="/" className={cls('/')}><i className="fas fa-home" /> 首页</a>
        <a href="/channels" className={cls('/channels')}><i className="fas fa-broadcast-tower" /> 频道</a>
        <a href="/market" className={cls('/market')}><i className="fas fa-store" /> 泓市场</a>
        <a href="/games" className={cls('/games')}><i className="fas fa-gamepad" /> 小游戏</a>
        <a href="/music" className={cls('/music')}><i className="fas fa-music" /> 音乐</a>
        {me?.role === 'admin' && <a href="/admin" className={cls('/admin')}><i className="fas fa-shield-halved" /> 后台</a>}
        {me ? <><a href="/new" className="nav-btn"><i className="fas fa-pen" /> 发帖</a><NotificationBell /><button className="nav-btn nav-btn-outline" onClick={logout}>退出</button></> : <><a href="/login" className="nav-btn nav-btn-outline">登录</a><a href="/register" className="nav-btn">注册</a></>}
      </div>
    </div>
  </nav>
}

function NotificationBell() {
  const [n, setN] = useState(0)
  useEffect(() => {
    let alive = true
    const load = () => api('/api/me/notifications?page_size=1').then(d => alive && setN(d.unread || 0)).catch(() => {})
    load()
    const onRefresh = () => load()
    window.addEventListener('notifications:refresh', onRefresh)
    const t = setInterval(load, 5000)
    return () => { alive = false; clearInterval(t); window.removeEventListener('notifications:refresh', onRefresh) }
  }, [])
  const me = JSON.parse(localStorage.getItem('yhdet_user') || '{}')
  return <a className="nav-link nav-user-with-badge" href={`/user/${me.id || ''}#comments`} title="个人主页">{me.username || '我的主页'}{n > 0 && <span className="bubble-badge red-badge">{n > 99 ? '99+' : n}</span>}</a>
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

function SearchBox({ onSearch, searching = false, initialQuery = '', initialType = 'posts' }) {
  const [q, setQ] = useState(initialQuery)
  const [type, setType] = useState(initialType)
  return <div className="search-container animate-fadeInUp"><form action="/" method="get" style={{ display: 'flex', gap: 12, width: '100%', flexWrap: 'wrap' }} onSubmit={(e) => { e.preventDefault(); onSearch(q, type) }}>
    <div className="search-input-wrap"><i className="fas fa-search" /><input type="text" name="q" className="search-input" placeholder="搜索帖子或用户..." value={q} onChange={e => setQ(e.target.value)} /></div>
    <select name="type" className="search-select" value={type} onChange={e => setType(e.target.value)}><option value="posts">搜索帖子</option><option value="users">搜索用户</option></select>
    <button type="submit" className="btn btn-primary" disabled={searching}><i className={`fas ${searching ? 'fa-spinner fa-spin' : 'fa-search'}`} /> {searching ? '搜索中' : '搜索'}</button>
  </form></div>
}

function htmlText(s = '') { return s.replace(/<br\s*\/?>/gi, '\n').replace(/<[^>]+>/g, '') }
function parseTimeValue(s = '') {
  if (!s) return null
  let normalized = String(s).trim().replace(' ', 'T')
  // Backend stores channel feed times in UTC but often without a timezone suffix.
  // Treat timezone-less timestamps as UTC to avoid showing "8小时前" on CN browsers.
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$/.test(normalized)) normalized += 'Z'
  const d = new Date(normalized)
  return Number.isNaN(d.getTime()) ? null : d
}
function formatAbsoluteTime(d) {
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}
function displayTime(s = '') { return s ? String(s).replace('T', ' ').slice(0, 19) : '' }
function displayDate(s = '') {
  const d = parseTimeValue(s)
  if (!d) return s ? String(s).slice(0, 10) : ''
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}
function orderStatusText(s = '') { return s === 'SUCCESS' ? '已完成' : s === 'PENDING' ? '待处理' : s === 'PENDING_AUDIT' ? '待审核' : s === 'REJECTED' ? '已拒绝/已退款' : s === 'FAILED' ? '失败' : s }
function isAvatarBorderItem(item = {}) {
  try { return JSON.parse(item.payload_json || '{}')?.effect === 'avatar_border_style' } catch { return /^头像颜色卡|^谷歌至尊四色环/.test(item.title || '') }
}
function decodeOrderNote(text = '') {
  if (!text) return ''
  try {
    const obj = JSON.parse(text)
    if (obj.type && obj.value) return `${obj.type === 'rename' ? '申请新用户名' : obj.type === 'title' ? '申请头衔' : obj.type}: ${obj.value}`
    return obj.note || obj.address || Object.entries(obj).map(([k,v]) => `${k}: ${v}`).join(' / ')
  } catch { return text }
}
function orderItemTypeLabel(type = '') {
  return { AVATAR_FRAME: '头像环', USERNAME_BADGE: '昵称图标', TITLE: '专属称号', THEME: '主页皮肤', COMMENT_THEME: '评论纸' }[type] || '装扮'
}
function OrderRow({ order, onChanged }) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const detail = decodeOrderNote(order.delivered_content || order.payload || order.shipping_info || '')
  async function toggleEquip(e) {
    e.stopPropagation()
    if (!order.equip_supported || order.status !== 'SUCCESS') return
    setBusy(true)
    try {
      const path = order.is_equipped ? '/api/market/records/unequip' : '/api/market/records/equip'
      const res = await api(path, { method: 'POST', body: JSON.stringify({ record_id: order.id, item_type: order.item_type }) })
      if (res.user) syncStoredUser(res.user)
      onChanged?.(res, order)
      notify(res.message || (order.is_equipped ? '已恢复默认' : '已启用装扮'), 'success')
    } catch (err) { notify(err.message, 'error') } finally { setBusy(false) }
  }
  const canEquip = order.equip_supported && order.status === 'SUCCESS'
  return <div className={`post-item order-row ${order.is_equipped ? 'order-equipped' : ''}`}><div role="button" tabIndex={0} className="order-row-main" onClick={() => setOpen(!open)} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') setOpen(v => !v) }}><div><div className="post-title"><i className={`fas ${order.cover_icon || 'fa-gift'}`} /> {order.title || order.item_title}{order.is_equipped && <span className="order-equipped-badge"><i className="fas fa-check" /> 使用中</span>}</div><div className="post-meta"><span>{order.cost_points || order.price} 泓币</span><span>{relativeTime(order.created_at)}</span><span>{orderStatusText(order.status)}</span>{order.item_type && <span>{orderItemTypeLabel(order.item_type)}</span>}</div></div><div className="order-row-actions">{canEquip && <button type="button" className={`btn btn-sm ${order.is_equipped ? 'btn-secondary' : 'btn-primary'} order-equip-btn`} onClick={toggleEquip}>{busy ? '处理中...' : order.is_equipped ? '恢复默认' : '立即启用'}</button>}<i className={`fas ${open ? 'fa-chevron-up' : 'fa-chevron-down'}`} /></div></div>{open && <div className="order-detail"><p><b>兑换时间：</b>{displayTime(order.created_at)}</p><p><b>处理状态：</b>{orderStatusText(order.status)}</p>{order.item_type && <p><b>装扮类型：</b>{orderItemTypeLabel(order.item_type)}{order.is_equipped ? ' · 当前使用中' : ''}</p>}{detail ? <p><b>兑换详情：</b>{detail}</p> : <p><b>兑换详情：</b>{order.status === 'PENDING' ? '等待管理员处理' : '暂无额外内容'}</p>}{order.fulfilled_at && <p><b>完成时间：</b>{displayTime(order.fulfilled_at)}</p>}</div>}</div>
}
function communityAge(days) {
  if (days === null || days === undefined || days === '') return ''
  const n = Number(days)
  if (!Number.isFinite(n)) return ''
  if (n >= 365) return `${Math.floor(n / 365)}年${n % 365 ? `${n % 365}天` : ''}`
  return `${n}天`
}
function formatCount(v, suffix = '') {
  if (v === null || v === undefined || v === '') return ''
  const n = Number(v)
  if (!Number.isFinite(n)) return ''
  return `${n.toLocaleString()}${suffix}`
}
function relativeTime(s = '') {
  const d = parseTimeValue(s)
  if (!d) return s
  const diff = Math.max(0, Date.now() - d.getTime())
  const min = Math.floor(diff / 60000)
  if (min < 1) return '刚刚'
  if (min < 60) return `${min}分钟前`
  const hours = Math.floor(min / 60)
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days}天前`
  const months = Math.floor(days / 30)
  if (months < 12) return `${months}个月前`
  return `${Math.floor(months / 12)}年前`
}
function sourceLinkLabel(url = '') {
  const u = String(url).toLowerCase()
  if (u.includes('linux.do')) return '查看 Linux.do 原帖'
  if (u.includes('forum.naixi.net')) return '查看奶昔论坛原帖'
  return '查看来源原帖'
}

function ProfileStats({ stats = {} }) {
  const items = [
    ['加入社区', displayDate(stats.joined_at), 'fa-calendar-plus'],
    ['社区年龄', communityAge(stats.community_age_days), 'fa-seedling'],
    ['发布帖子', formatCount(stats.posts_count, ' 篇'), 'fa-pen-nib'],
    ['发出评论', formatCount(stats.comments_count, ' 条'), 'fa-comment-dots'],
    ['浏览帖子', formatCount(stats.views_count, ' 次'), 'fa-eye'],
    ['单帖最高评论', formatCount(stats.max_post_comments, ' 条'), 'fa-fire'],
    ['最后活跃', relativeTime(stats.last_active_at), 'fa-clock'],
    ['泓币资产', `${Number(stats.hongcoin_balance || 0).toLocaleString()} 枚`, 'fa-coins', 'market'],
  ].filter(x => x[1] !== '' && x[1] !== null && x[1] !== undefined)
  if (!items.length) return null
  return <div className="profile-stats-grid">{items.map(([label, value, icon, type]) => <div className={`profile-stat ${type === 'market' ? 'profile-stat-market' : ''}`} key={label}><span><i className={`fas ${icon}`} /> {label}</span><b>{value}</b>{type === 'market' && <a className="profile-market-entry" href="/market">进入泓市场 <i className="fas fa-arrow-right" /></a>}</div>)}</div>
}

function SiteFooter({ site = defaultSite }) {
  const stats = site.stats || {}
  const runtime = site.runtime || {}
  return <footer className="footer site-footer">
    <div className="footer-brand">{site.site_name || '泓聊社区'}</div>
    <div className="footer-meta">
      {runtime.uptime_text && <span><i className="fas fa-signal" /> 已运行 {runtime.uptime_text}</span>}
      {runtime.started_at && <span><i className="far fa-clock" /> 启动 {displayTime(runtime.started_at)}</span>}
      {stats.users !== undefined && <span><i className="fas fa-users" /> 用户 {stats.users}</span>}
      {stats.posts !== undefined && <span><i className="fas fa-file-lines" /> 帖子 {stats.posts}</span>}
      {stats.comments !== undefined && <span><i className="fas fa-comments" /> 评论 {stats.comments}</span>}
      {runtime.version && <span>v{runtime.version}</span>}
    </div>
  </footer>
}


function useFlipList(items, keyFn = x => x.id) {
  const refs = useRef(new Map())
  const prevRects = useRef(new Map())
  useLayoutEffect(() => {
    const nextRects = new Map()
    refs.current.forEach((el, key) => {
      if (!el) return
      const next = el.getBoundingClientRect()
      nextRects.set(key, next)
      const prev = prevRects.current.get(key)
      if (!prev) return
      const dx = prev.left - next.left
      const dy = prev.top - next.top
      if (!dx && !dy) return
      el.animate([
        { transform: `translate(${dx}px, ${dy}px)`, boxShadow: '0 10px 30px rgba(74,144,217,.18)' },
        { transform: 'translate(0, 0)', boxShadow: '0 0 0 rgba(74,144,217,0)' }
      ], { duration: 360, easing: 'cubic-bezier(.2,.8,.2,1)' })
    })
    prevRects.current = nextRects
  }, [items.map(keyFn).join('|')])
  return key => el => {
    if (el) refs.current.set(key, el)
    else refs.current.delete(key)
  }
}

function PostItem({ post, innerRef }) {
  return <a ref={innerRef} href={`/post/${post.id}`} className={`post-item ${post.bumped ? 'bumped' : ''}`} style={{ textDecoration: 'none', display: 'block' }} onMouseDown={e => e.currentTarget.classList.add('is-active')} onBlur={e => e.currentTarget.classList.remove('is-active')}>
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
      <AvatarRing user={post} src={post.avatar} size={48} className="post-avatar-ring" />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="post-title">{post.pinned && <span className="pin-badge"><i className="fas fa-thumbtack" /> 置顶</span>}{post.title}</div>
        <div className="post-preview">{htmlText(post.preview || post.content)}</div>
        <div className="post-meta"><div className="post-meta-item"><a href={`/user/${post.user_id}`} className={`post-author-name ${usernameClass(post)}`} onClick={e => e.stopPropagation()}>{post.author}</a><UsernameBadge user={post} />{post.role && <span className="role-badge role-super-admin"><i className="fas fa-crown" /> {post.role}</span>}</div><div className="post-meta-item"><i className="far fa-clock" /> {relativeTime(post.time)}</div><div className="post-stats"><span className="post-stat"><i className="far fa-comment" /> {post.comments || ''}</span><span className="post-stat"><i className="far fa-eye" /> {post.views || ''}</span></div></div>
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
  return <div className="card animate-fadeInUp"><div className="card-header"><h3><i className="fas fa-users" /> 用户搜索结果</h3></div><div className="card-body"><div className="user-grid">{users.length ? users.map(u => <a className="user-card" href={`/user/${u.id}`} key={u.id} style={{ textDecoration: 'none' }}><AvatarRing user={u} src={u.avatar} size={62} className="user-card-avatar-ring" /><div className={`user-card-name ${usernameClass(u)}`}>{u.username}<UsernameBadge user={u} /></div><div className="user-card-bio">{u.role_label || '社区用户'}</div></a>) : <div className="empty-state"><i className="fas fa-search" /><p>没有找到用户</p></div>}</div></div></div>
}

function Home() {
  const PAGE_SIZE = 30
  const LOAD_COOLDOWN_MS = 1100
  const [data, setData] = useState(() => homeStateCache?.data || null)
  const [posts, setPosts] = useState(() => homeStateCache?.posts || [])
  const [users, setUsers] = useState(() => homeStateCache?.users || null)
  const [usersPage, setUsersPage] = useState(() => homeStateCache?.usersPage || 1)
  const [usersHasMore, setUsersHasMore] = useState(() => homeStateCache?.usersHasMore || false)
  const [usersLoadingMore, setUsersLoadingMore] = useState(false)
  const [searching, setSearching] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const [hasMore, setHasMore] = useState(() => homeStateCache?.hasMore ?? true)
  const [totalPosts, setTotalPosts] = useState(() => homeStateCache?.totalPosts || 0)
  const [query, setQuery] = useState(() => homeStateCache?.query || '')
  const [err, setErr] = useState('')
  const loadingRef = useRef(false)
  const lastLoadAtRef = useRef(0)
  const searchTypeRef = useRef(homeStateCache?.searchType || 'posts')
  const restoreScrollRef = useRef(homeStateCache?.scrollY || 0)
  const restoredScrollRef = useRef(false)
  const queryRef = useRef(query)
  const usersRef = useRef(users)
  const feedReconnectRef = useRef(0)
  const postFlipRef = useFlipList(posts)

  useEffect(() => { queryRef.current = query }, [query])
  useEffect(() => { usersRef.current = users }, [users])

  async function loadPostsPage({ reset = false, q = query, silent = false } = {}) {
    if (loadingRef.current) return
    const elapsed = Date.now() - lastLoadAtRef.current
    if (!reset && elapsed < LOAD_COOLDOWN_MS) return
    loadingRef.current = true
    lastLoadAtRef.current = Date.now()
    if (reset) setSearching(true)
    else setLoadingMore(true)
    try {
      const nextPage = reset ? 1 : Math.floor(posts.length / PAGE_SIZE) + 1
      const res = await api(`/api/posts?page=${nextPage}&page_size=${PAGE_SIZE}&q=${encodeURIComponent(q || '')}`)
      setUsers(null)
      setPosts(prev => reset ? (res.items || []) : [...prev, ...(res.items || [])])
      setHasMore(Boolean(res.has_more))
      setTotalPosts(res.total || 0)
      setErr('')
    } catch (e) {
      if (!silent) setErr(e.message)
    } finally {
      loadingRef.current = false
      setSearching(false)
      setLoadingMore(false)
    }
  }

  useEffect(() => {
    let alive = true
    let timer = 0
    const loadHome = (silent = false) => api('/api/home').then(d => {
      if (!alive) return
      setData(d); if (d.settings) chromeCache = d
    }).catch(e => { if (alive && !silent) setErr(e.message) })
    loadHome(false).then(() => { if (alive && !homeStateCache?.posts?.length) loadPostsPage({ reset: true, q: '', silent: true }) })
    timer = setInterval(() => { if (!document.hidden) loadHome(true) }, 15000)
    return () => { alive = false; clearInterval(timer) }
  }, [])

  useEffect(() => {
    let closed = false
    let ws = null
    let heartbeat = 0
    const connect = () => {
      ws = new WebSocket(websocketUrl('/ws/feed'))
      ws.onopen = () => {
        if (heartbeat) clearInterval(heartbeat)
        heartbeat = setInterval(() => { if (ws?.readyState === WebSocket.OPEN) ws.send('ping') }, 12000)
      }
      ws.onmessage = ev => {
        try {
          const msg = JSON.parse(ev.data)
          if (!['post_created', 'post_bumped'].includes(msg.type) || !msg.post) return
          // Only auto-update the normal latest-post feed. Do not disturb search/user-result views.
          if (queryRef.current || usersRef.current) return
          setPosts(prev => {
            const existed = prev.some(p => p.id === msg.post.id)
            const merged = existed ? { ...prev.find(p => p.id === msg.post.id), ...msg.post, bumped: msg.type === 'post_bumped' } : msg.post
            return [merged, ...prev.filter(p => p.id !== msg.post.id)]
          })
          if (msg.type === 'post_created') setTotalPosts(v => Number(v || 0) + 1)
        } catch (_) {}
      }
      ws.onclose = () => {
        if (heartbeat) clearInterval(heartbeat)
        if (!closed) feedReconnectRef.current = setTimeout(connect, 1500)
      }
      ws.onerror = () => { try { ws.close() } catch (_) {} }
    }
    connect()
    return () => {
      closed = true
      if (heartbeat) clearInterval(heartbeat)
      if (feedReconnectRef.current) clearTimeout(feedReconnectRef.current)
      try { ws?.close() } catch (_) {}
    }
  }, [])

  useEffect(() => {
    const preservedScroll = restoredScrollRef.current ? window.scrollY : restoreScrollRef.current
    homeStateCache = { data, posts, users, usersPage, usersHasMore, hasMore, totalPosts, query, searchType: searchTypeRef.current, scrollY: preservedScroll }
  }, [data, posts, users, usersPage, usersHasMore, hasMore, totalPosts, query])
  useEffect(() => {
    if (restoreScrollRef.current) requestAnimationFrame(() => { window.scrollTo({ top: restoreScrollRef.current, behavior: 'auto' }); restoredScrollRef.current = true })
    else restoredScrollRef.current = true
    const saveScroll = () => {
      if (new URL(currentRoute(), location.origin).pathname === '/' && homeStateCache) homeStateCache.scrollY = window.scrollY
    }
    window.addEventListener('scroll', saveScroll, { passive: true })
    return () => { saveScroll(); window.removeEventListener('scroll', saveScroll) }
  }, [])

  useEffect(() => {
    if (users) return
    const onScroll = () => {
      if (!hasMore || loadingRef.current || searching || loadingMore) return
      const remain = document.documentElement.scrollHeight - window.scrollY - window.innerHeight
      if (remain < 480) loadPostsPage({ reset: false })
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    onScroll()
    return () => window.removeEventListener('scroll', onScroll)
  }, [hasMore, searching, loadingMore, users, posts.length, query])

  async function onSearch(q, type) {
    setErr('')
    searchTypeRef.current = type
    setQuery(q || '')
    if (type === 'users') {
      setSearching(true)
      try {
        const res = await api(`/api/search?q=${encodeURIComponent(q)}&type=users&page=1&page_size=30`)
        setUsers(res.items || [])
        setUsersPage(1)
        setUsersHasMore(Boolean(res.has_more))
        setHasMore(false)
      } catch(e) { setErr(e.message) }
      finally { setSearching(false) }
      return
    }
    await loadPostsPage({ reset: true, q: q || '' })
  }
  async function loadMoreUsers() {
    if (!usersHasMore || usersLoadingMore) return
    setUsersLoadingMore(true)
    try {
      const np = usersPage + 1
      const res = await api(`/api/search?q=${encodeURIComponent(query)}&type=users&page=${np}&page_size=30`)
      setUsers(v => [...(v || []), ...(res.items || [])])
      setUsersPage(np)
      setUsersHasMore(Boolean(res.has_more))
    } catch(e) { setErr(e.message) }
    finally { setUsersLoadingMore(false) }
  }
  if (!data) return <HomeSkeleton />
  return <><SiteStats stats={data.stats} /><LedBanner banners={data.banners} /><div className="main-content"><SearchBox onSearch={onSearch} searching={searching} initialQuery={query} initialType={searchTypeRef.current} />{err && <div className="alert alert-error">{err}</div>}<div className="home-layout"><div>{users ? <UserResults users={users} hasMore={usersHasMore} loadingMore={usersLoadingMore} onMore={loadMoreUsers} /> : <div className="card animate-fadeInUp"><div className="card-header"><h3><i className="fas fa-fire" style={{ color: 'var(--secondary)' }} /> 最新帖子</h3>{searching && <span className="mini-busy">刷新中</span>}</div><div>{searching && posts.length === 0 ? <PostListSkeleton count={5} /> : posts.length ? posts.map(p => <PostItem key={p.id} post={p} innerRef={postFlipRef(p.id)} />) : <div className="empty-state"><i className="fas fa-search" /><p>没有找到帖子</p></div>}{posts.length > 0 && <div className="infinite-loader">{loadingMore ? <><i className="fas fa-spinner fa-spin" /> 正在加载下一页...</> : hasMore ? '滑到底部自动加载更多' : '已经到底了'}</div>}</div></div>}</div><Sidebar donors={data.donors} notice={data.notice} /></div></div></>
}

function CaptchaBox({ value, onChange, captchaId, onChallenge }) {
  const [code, setCode] = useState('')
  const [loading, setLoading] = useState(false)
  const canvasRef = React.useRef(null)
  const gen = async () => {
    setLoading(true)
    try {
      const res = await api('/api/captcha', { method: 'POST' })
      setCode(res.code || '')
      onChange('')
      onChallenge?.(res.id || '')
    } catch (e) {
      setCode('ERROR')
      onChallenge?.('')
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => { gen() }, [])
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
    <p className="captcha-hint">{loading ? '正在刷新...' : '点击图片刷新'}{captchaId ? '' : '，未获取到请再点一次'}</p>
  </div>
}

function AuthPage({ mode, setMe, site = defaultSite }) {
  const isLogin = mode === 'login'
  useEffect(() => { document.title = `${isLogin ? '登录' : '注册'} - ${(site.site_name || '泓聊社区')}` }, [isLogin, site.site_name])
  const [form, setForm] = useState({ username: '', email: '', email_code: '', password: '', captcha_id: '', captcha: '' })
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
  useEffect(() => {
    const msg = new URLSearchParams(location.search).get('oauth_error')
    if (msg) setErr(decodeURIComponent(msg))
  }, [])
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
    if (site.captcha_enabled && (!form.captcha_id || !form.captcha.trim())) return setErr('请填写验证码')
    if (!isLogin && !form.email.trim()) return setErr('请填写邮箱')
    setLoading(true)
    try {
      const payload = { ...form, username: form.username.trim(), email: form.email.trim() || null }
      const res = await api(isLogin ? '/api/login' : '/api/register', { method: 'POST', body: JSON.stringify(payload) })
      localStorage.setItem(tokenKey, res.token); localStorage.setItem('yhdet_user', JSON.stringify(res.user)); setMe(res.user); notify(isLogin ? '登录成功' : '注册成功', 'success'); navigate('/')
    } catch (e) { setErr(e.message); notify(e.message, 'error') } finally { setLoading(false) }
  }
  return <div className="auth-page">
    <div className={isLogin ? 'login-card' : 'register-card'}>
      <div className={isLogin ? 'login-header' : 'register-header'}><h1>{isLogin ? '登录' : '注册'}</h1><p>{site.site_name || '泓聊社区'}</p></div>
      {err && <div className="alert alert-error">{err}</div>}
      <form onSubmit={submit}>
        <div className="form-group"><label className="form-label" htmlFor="username">用户名</label><input id="username" type="text" className="form-input" placeholder="请输入用户名" required value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} /></div>
        {!isLogin && <div className="form-group"><label className="form-label" htmlFor="email">邮箱</label><input id="email" type="text" className="form-input" placeholder="请输入邮箱地址" required value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} /><p className="form-hint">没有邮箱？填 手机号@phoneTEL（如：13812345678@phoneTEL）</p></div>}
        {!isLogin && <div className="form-group"><label className="form-label">邮箱验证码</label><div style={{ display: 'flex', gap: 10 }}><input type="text" className="form-input" placeholder="请输入6位邮箱验证码" required maxLength={6} style={{ flex: 1 }} value={form.email_code} onChange={e => setForm({ ...form, email_code: e.target.value })} /><button type="button" className="btn btn-primary send-code-btn" disabled={sending || countdown > 0} onClick={sendEmailCode}>{sending ? '发送中...' : countdown > 0 ? `${countdown}s后重发` : '发送验证码'}</button></div><p className="form-hint" style={{ color: hintColor }}>{hint}</p></div>}
        <div className="form-group"><label className="form-label" htmlFor="password">密码</label><input id="password" type="password" className="form-input" placeholder="请输入密码" required minLength={4} value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} /></div>
        {site.captcha_enabled && <CaptchaBox value={form.captcha} captchaId={form.captcha_id} onChange={captcha => setForm({ ...form, captcha })} onChallenge={captcha_id => setForm(f => ({ ...f, captcha_id, captcha: '' }))} />}
        <button type="submit" className="btn btn-primary auth-submit" disabled={loading}>{loading ? '提交中...' : (isLogin ? '登录' : '注册')}</button>
      </form>
      {site.qidao_oauth_enabled && <div className="oauth-login"><div className="oauth-divider"><span>或使用第三方登录</span></div><a className="btn btn-secondary qidao-login" href={`/api/oauth/qidao/start?next=${encodeURIComponent('/')}`}><i className="fas fa-island-tropical" /> 栖岛账号登录</a></div>}
      <div className={isLogin ? 'login-footer' : 'register-footer'}>{isLogin ? <>没有账号？<a href="/register">立即注册</a></> : <>已有账号？<a href="/login">立即登录</a></>}</div>
    </div>
    <div className="sticker"><img src="/static/sticker.png" alt="" loading="lazy" decoding="async" onError={e => { e.currentTarget.style.display = 'none' }} /></div>
  </div>
}

function NewPost({ me }) {
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [err, setErr] = useState('')
  const [saving, setSaving] = useState(false)
  if (!me) return <div className="main-content"><div className="alert alert-info"><i className="fas fa-info-circle" /> 请先 <a href="/login">登录</a> 后发帖</div></div>
  async function submit(e) {
    e.preventDefault(); setErr('')
    if (!title.trim() || !content.trim()) return setErr('标题和内容不能为空')
    setSaving(true)
    try {
      const res = await api('/api/posts', { method: 'POST', body: JSON.stringify({ title: title.trim(), content: content.trim() }) })
      const newPost = res.post || { id: res.id, title:title.trim(), content:content.trim(), preview:content.trim(), author:me.username, avatar:me.avatar, avatar_border_style:me.avatar_border_style, user_id:me.id, time:new Date().toISOString(), comments:0, views:0 }
      homeStateCache = homeStateCache ? { ...homeStateCache, posts: [newPost, ...(homeStateCache.posts || []).filter(p => p.id !== newPost.id)], totalPosts: (homeStateCache.totalPosts || 0) + 1 } : { data:null, posts:[newPost], totalPosts:1, scrollY:0 }
      setTitle(''); setContent('')
      if (res.current_points !== undefined) mergeStoredUser({ available_points: res.current_points })
      notify('发布成功，已同步到首页', 'success')
      navigate(`/post/${newPost.id}`)
    } catch (e) { setErr(e.message); notify(e.message, 'error') } finally { setSaving(false) }
  }
  return <div className="main-content"><div className="card"><div className="card-header"><h3><i className="fas fa-pen" /> 发布帖子</h3></div><div className="card-body">{err && <div className="alert alert-error">{err}</div>}<form onSubmit={submit}><div className="form-group"><label className="form-label">标题</label><input className="form-input" required maxLength={120} value={title} onChange={e => setTitle(e.target.value)} placeholder="请输入标题" disabled={saving} /></div><div className="form-group"><label className="form-label">内容</label><textarea className="form-textarea" required maxLength={10000} value={content} onChange={e => setContent(e.target.value)} placeholder="请输入内容" style={{ minHeight: 220 }} disabled={saving} /></div><button className="btn btn-primary" disabled={saving}><i className={`fas ${saving ? 'fa-spinner fa-spin' : 'fa-paper-plane'}`} /> {saving ? '发布中' : '发布'}</button></form></div></div></div>
}

function renderContent(content = '') {
  return htmlText(content).split(/\n{2,}/).map((para, idx) => <p key={idx}>{para}</p>)
}

function inlineMarkdown(text = '') {
  const parts = String(text).split(/(`[^`]+`|~~[^~]+~~|\*\*[^*]+\*\*|\*[^*]+\*|\[[^\]]+\]\([^\s)]+\))/g).filter(Boolean)
  return parts.map((part, idx) => {
    if (/^`[^`]+`$/.test(part)) return <code key={idx}>{part.slice(1, -1)}</code>
    if (/^~~[^~]+~~$/.test(part)) return <del key={idx}>{part.slice(2, -2)}</del>
    if (/^\*\*[^*]+\*\*$/.test(part)) return <strong key={idx}>{part.slice(2, -2)}</strong>
    if (/^\*[^*]+\*$/.test(part)) return <em key={idx}>{part.slice(1, -1)}</em>
    const m = part.match(/^\[([^\]]+)\]\(([^\s)]+)\)$/)
    if (m) return <a key={idx} href={m[2]} target="_blank" rel="noreferrer">{m[1]}</a>
    return <React.Fragment key={idx}>{part}</React.Fragment>
  })
}

function MarkdownRenderer({ content = '', compact = false }) {
  const src = String(content || '').trim()
  if (!src) return null
  const blocks = src.split(/\n{2,}/).filter(Boolean)
  let inCode = false
  const rendered = []
  let codeLines = []
  let codeLang = ''
  const flushCode = key => { rendered.push(<pre key={`code-${key}`} className="code-block"><code>{codeLines.join('\n')}</code></pre>); codeLines = []; codeLang = '' }
  blocks.forEach((block, idx) => {
    if (block.startsWith('```')) {
      const lines = block.split('\n')
      codeLang = lines[0].replace('```', '').trim()
      const end = lines.lastIndexOf('```')
      codeLines = end > 0 ? lines.slice(1, end) : lines.slice(1)
      rendered.push(<pre key={idx} className="code-block" data-lang={codeLang}><code>{codeLines.join('\n')}</code></pre>)
      return
    }
    const lines = block.split('\n')
    if (/^#{1,3}\s+/.test(lines[0].trim())) { const level = lines[0].trim().match(/^#+/)[0].length; const text = lines[0].replace(/^#{1,3}\s+/, ''); const Tag = `h${Math.min(3, level)}`; rendered.push(<Tag key={idx}>{inlineMarkdown(text)}</Tag>); return }
    if (lines.every(line => line.trim().startsWith('>'))) { rendered.push(<blockquote key={idx}>{lines.map(line => line.replace(/^>\s?/, '')).join('\n')}</blockquote>); return }
    if (lines.every(line => /^[-*]\s+\[[ x]\]\s+/i.test(line.trim()))) { rendered.push(<ul key={idx} className="task-list">{lines.map((line, i) => { const checked = /^[-*]\s+\[x\]/i.test(line.trim()); return <li key={i}><input type="checkbox" checked={checked} readOnly />{inlineMarkdown(line.trim().replace(/^[-*]\s+\[[ x]\]\s+/i, ''))}</li> })}</ul>); return }
    if (lines.every(line => /^[-*]\s+/.test(line.trim()))) { rendered.push(<ul key={idx}>{lines.map((line, i) => <li key={i}>{inlineMarkdown(line.trim().replace(/^[-*]\s+/, ''))}</li>)}</ul>); return }
    if (lines.every(line => /^\d+\.\s+/.test(line.trim()))) { rendered.push(<ol key={idx}>{lines.map((line, i) => <li key={i}>{inlineMarkdown(line.trim().replace(/^\d+\.\s+/, ''))}</li>)}</ol>); return }
    if (lines.length >= 2 && lines[0].includes('|') && /^\s*\|?\s*:?-{3,}/.test(lines[1])) { const headers = lines[0].split('|').map(x=>x.trim()).filter(Boolean); const rows = lines.slice(2).map(r=>r.split('|').map(x=>x.trim()).filter(Boolean)); rendered.push(<div className="md-table-wrap" key={idx}><table><thead><tr>{headers.map(h=><th key={h}>{inlineMarkdown(h)}</th>)}</tr></thead><tbody>{rows.map((r,i)=><tr key={i}>{r.map((cell,j)=><td key={j}>{inlineMarkdown(cell)}</td>)}</tr>)}</tbody></table></div>); return }
    rendered.push(<p key={idx}>{lines.map((line, i) => <React.Fragment key={i}>{inlineMarkdown(line)}{i < lines.length - 1 && <br />}</React.Fragment>)}</p>)
  })
  return <div className={`markdown-body ${compact ? 'comment-markdown compact' : 'comment-markdown'}`}>{rendered}</div>
}

function websocketUrl(path) {
  const base = API_BASE || ''
  const origin = base ? new URL(base, location.origin) : location
  const proto = origin.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${origin.host}${path}`
}

function useTopicPresence(topicId, me, onTopicEvent) {
  const [presence, setPresence] = useState({ online_count: 0, viewers: [], overflow: 0, typing: [], editing: [] })
  const wsRef = useRef(null)
  const typingTimerRef = useRef(null)
  const connectedRef = useRef(false)
  const eventRef = useRef(onTopicEvent)
  useEffect(() => { eventRef.current = onTopicEvent }, [onTopicEvent])
  useEffect(() => {
    if (!topicId) return
    let closed = false
    let reconnectTimer = null
    let heartbeat = null
    const connect = () => {
      const token = localStorage.getItem(tokenKey) || ''
      const qs = token ? `?token=${encodeURIComponent(token)}` : ''
      const ws = new WebSocket(websocketUrl(`/ws/topics/${topicId}/presence${qs}`))
      wsRef.current = ws
      ws.onopen = () => { connectedRef.current = true; ws.send(JSON.stringify({ type: 'heartbeat' })) }
      ws.onmessage = e => {
        try {
          const msg = JSON.parse(e.data)
          if (msg.type === 'presence_snapshot') setPresence(msg)
          if (msg.type && msg.type.startsWith('comment_')) eventRef.current?.(msg)
        } catch {}
      }
      ws.onclose = () => {
        connectedRef.current = false
        if (!closed) reconnectTimer = setTimeout(connect, 1200)
      }
      heartbeat = setInterval(() => { if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'heartbeat' })) }, 12000)
    }
    connect()
    return () => { closed = true; clearTimeout(reconnectTimer); clearInterval(heartbeat); connectedRef.current = false; try { wsRef.current?.close() } catch {}; wsRef.current = null; clearTimeout(typingTimerRef.current) }
  }, [topicId, me?.id])
  const send = payload => {
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(payload))
  }
  const sendTyping = () => {
    if (!me) return
    send({ type: 'typing' })
    clearTimeout(typingTimerRef.current)
    typingTimerRef.current = setTimeout(() => send({ type: 'typing_end' }), 2500)
  }
  const sendTypingEnd = () => send({ type: 'typing_end' })
  const sendEditing = commentId => { if (me && commentId) send({ type: 'editing', comment_id: commentId }) }
  const sendEditingEnd = commentId => { if (commentId) send({ type: 'editing_end', comment_id: commentId }) }
  return { presence, sendTyping, sendTypingEnd, sendEditing, sendEditingEnd }
}

function PresenceBar({ presence }) {
  const viewers = presence.viewers || []
  return <div className="presence-bar">
    <div className="presence-avatars" title={`${presence.online_count || 0} 人正在浏览`}>
      {viewers.map(u => <AvatarRing key={u.id} user={u} src={u.avatar} size={24} className="presence-avatar-ring" title={u.username} />)}
      {presence.overflow > 0 && <span className="presence-more">+{presence.overflow}</span>}
    </div>
    <span className="presence-count"><i className="fas fa-circle" /> {presence.online_count || 0} 人正在浏览这个帖子</span>
  </div>
}

function PresenceActivity({ presence }) {
  const typing = (presence.typing || []).filter(u => !u.anonymous)
  const editing = (presence.editing || []).map(x => x.user).filter(Boolean)
  const unique = []
  const seen = new Set()
  ;[...typing, ...editing].forEach(u => { const key = String(u.id); if (!seen.has(key)) { seen.add(key); unique.push(u) } })
  if (!unique.length) return null
  const names = unique.slice(0, 2).map(u => u.username).join('、')
  const action = typing.length && editing.length ? '正在协作' : typing.length ? '正在输入' : '正在编辑'
  return <div className="presence-activity">
    <div className="presence-avatars compact" title={unique.map(u => u.username).join('、')}>
      {unique.slice(0, 5).map(u => <AvatarRing key={u.id} user={u} src={u.avatar} size={24} className="presence-avatar-ring" title={u.username} />)}
      {unique.length > 5 && <span className="presence-more">+{unique.length - 5}</span>}
    </div>
    <span><span className="typing-dot" /> {names}{unique.length > 2 ? ` 等 ${unique.length} 人` : ''} {action}...</span>
  </div>
}

function ReplyIndicator({ comment, onCancel, onJump }) {
  if (!comment) return null
  return <div className="reply-indicator"><button type="button" onClick={() => onJump?.(comment.id)}><i className="fas fa-reply" /> 回复 @{comment.author}</button>{onCancel && <button type="button" className="reply-cancel" onClick={onCancel}>取消回复</button>}</div>
}

function OutgoingReplyLink({ comment, onJump }) {
  if (!comment.reply_to_comment_id) return null
  const title = comment.reply_to_deleted ? '回复一条已删除的评论' : `回复 @${comment.reply_to_author || '用户'}`
  return <button type="button" className={`outgoing-reply-link ${comment.reply_to_deleted ? 'deleted-ref' : ''}`} title={title} onClick={() => onJump(comment.reply_to_comment_id)}>
    <svg className="reply-arrow" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <path d="M11.6 5.2 16.2 9.8l-4.6 4.6" />
      <path d="M15.8 9.8H8.7c-3.1 0-5 1.8-5 4.8v.7" />
    </svg>
    <img src={safeAvatar(comment.reply_to_avatar)} alt={title} onError={onAvatarError} />
  </button>
}

function RepliesBar({ replies = [], expanded, setExpanded, onJump }) {
  if (!replies.length) return null
  const latest = replies[replies.length - 1]
  return <div className="replies-block">
    <div className="replies-bar">
      <button type="button" className="replies-toggle" onClick={() => setExpanded(!expanded)} aria-expanded={expanded}>
        <i className={`fas ${expanded ? 'fa-chevron-down' : 'fa-chevron-right'}`} />
        <span>{replies.length} 条回复</span>
      </button>
      <button type="button" className="jump-reply" onClick={() => onJump(latest.id)}>跳到最新回复</button>
    </div>
    {expanded && <div className="replies-expanded">
      {replies.map(r => <CommentCard key={`preview-${r.id}`} comment={r} onReply={() => {}} onEdit={() => {}} onDelete={() => {}} directReplies={[]} onJump={onJump} embedded />)}
    </div>}
  </div>
}

function CommentMenuPortal({ anchorRef, open, onClose, canEdit, canDelete, busy, onEdit, onRemove, onReport }) {
  const [pos, setPos] = useState(null)
  useEffect(() => {
    if (!open) return
    const update = () => {
      const anchor = anchorRef.current
      if (!anchor) return
      const r = anchor.getBoundingClientRect()
      const menuW = 128
      const menuH = 92
      const gap = 8
      const spaceBelow = window.innerHeight - r.bottom
      const dropup = spaceBelow < menuH + gap + 12 && r.top > menuH + gap
      setPos({
        left: Math.max(8, Math.min(window.innerWidth - menuW - 8, r.right - menuW)),
        top: dropup ? Math.max(8, r.top - menuH - gap) : Math.min(window.innerHeight - menuH - 8, r.bottom + gap),
        dropup,
      })
    }
    update()
    const close = e => {
      if (anchorRef.current?.contains(e.target)) return
      if (e.target.closest?.('.global-comment-menu')) return
      onClose()
    }
    const esc = e => { if (e.key === 'Escape') onClose() }
    window.addEventListener('resize', update)
    window.addEventListener('scroll', update, true)
    document.addEventListener('mousedown', close)
    document.addEventListener('touchstart', close, { passive: true })
    document.addEventListener('keydown', esc)
    return () => {
      window.removeEventListener('resize', update)
      window.removeEventListener('scroll', update, true)
      document.removeEventListener('mousedown', close)
      document.removeEventListener('touchstart', close)
      document.removeEventListener('keydown', esc)
    }
  }, [open, anchorRef, onClose])
  if (!open || !pos) return null
  return createPortal(
    <div className={`comment-menu global-comment-menu ${pos.dropup ? 'dropup' : 'dropdown'}`} style={{ left: pos.left, top: pos.top }}>
      <button type="button" disabled={!canEdit} onClick={onEdit}><i className="fas fa-pen" /> 编辑</button>
      <button type="button" disabled={!canDelete || busy} className="danger-link" onClick={onRemove}><i className="fas fa-trash" /> 删除</button>
      <button type="button" onClick={onReport}><i className="fas fa-flag" /> 举报</button>
    </div>,
    document.body
  )
}


function PostMoreMenuPortal({ anchorRef, open, onClose, onShare, onReport }) {
  const [pos, setPos] = useState(null)
  useLayoutEffect(() => {
    if (!open || !anchorRef.current) return
    const update = () => {
      const r = anchorRef.current.getBoundingClientRect()
      const width = 178
      const left = Math.min(window.innerWidth - width - 10, Math.max(10, r.right - width))
      const top = Math.min(window.innerHeight - 70, r.bottom + 8)
      setPos({ left, top })
    }
    update()
    const close = e => {
      if (anchorRef.current?.contains(e.target)) return
      if (e.target.closest?.('.global-post-menu')) return
      onClose()
    }
    const esc = e => { if (e.key === 'Escape') onClose() }
    window.addEventListener('resize', update)
    window.addEventListener('scroll', update, true)
    document.addEventListener('mousedown', close)
    document.addEventListener('touchstart', close, { passive: true })
    document.addEventListener('keydown', esc)
    return () => {
      window.removeEventListener('resize', update)
      window.removeEventListener('scroll', update, true)
      document.removeEventListener('mousedown', close)
      document.removeEventListener('touchstart', close)
      document.removeEventListener('keydown', esc)
    }
  }, [open, anchorRef, onClose])
  if (!open || !pos) return null
  return createPortal(
    <div className="comment-menu global-post-menu" style={{ left: pos.left, top: pos.top }}>
      <button type="button" onClick={onShare}><i className="fas fa-share-nodes" /> 分享 / 复制链接</button>
      <button type="button" onClick={onReport}><i className="fas fa-flag" /> 举报帖子</button>
    </div>,
    document.body
  )
}

function CommentCard({ comment, onReply, onEdit, onDelete, onReport, directReplies = [], onJump, embedded = false }) {
  const [busy, setBusy] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const moreBtnRef = useRef(null)
  const jump = onJump || ((id) => onReply({ ...comment, jump_to_id: id, quote_only: true }))
  async function remove() {
    if (!confirm('确定删除这条评论吗？如果没有人回复过，它会直接从评论区消失。')) return
    setBusy(true)
    try { await onDelete(comment); notify('评论已删除', 'success') } finally { setBusy(false) }
  }
  return <article id={embedded ? undefined : `comment-${comment.id}`} className={`comment-card topic-post regular ${commentThemeClass(comment)} ${comment.deleted ? 'is-deleted' : ''} ${embedded ? 'reply-preview-card' : ''} ${menuOpen ? 'menu-active' : ''}`}>
    <div className="topic-avatar"><AvatarRing user={comment} src={comment.avatar} size={48} className="topic-avatar-ring" href={`/user/${comment.user_id || ''}`} /></div>
    <div className="comment-main topic-body">
      <div className="comment-head topic-meta-data"><div className="names"><span className="first"><a className={`comment-author ${usernameClass(comment)}`} href={`/user/${comment.user_id || ''}`}>{comment.author}</a><UsernameBadge user={comment} /></span>{comment.role && <span className="user-title">{comment.role}</span>}</div><div className="post-infos"><OutgoingReplyLink comment={comment} onJump={jump} /><time className="post-info">{relativeTime(comment.time)}</time>{comment.edited && <span className="edited-mark">已编辑 · {relativeTime(comment.updated_at)}</span>}</div></div>
      <div className="regular-contents">
        {comment.deleted ? <div className="deleted-comment-box"><i className="fas fa-ban" /><div><strong>{comment.deleted_by_admin ? '此评论因违反社区规范已被管理员删除。' : '此评论已删除'}</strong>{comment.deleted_at && <span>删除于 {relativeTime(comment.deleted_at)}</span>}</div></div> : <MarkdownRenderer content={comment.content} compact />}
      </div>
      {!embedded && !comment.deleted && <nav className="comment-actions post-controls"><div className="actions"><button type="button" className="reply create" title="回复" aria-label="回复" onClick={() => onReply(comment)}><i className="fas fa-reply" /></button><div className="comment-more"><button ref={moreBtnRef} type="button" className="more-toggle" title="更多" aria-label="更多" aria-expanded={menuOpen} onClick={() => setMenuOpen(v => !v)}><i className="fas fa-ellipsis" /></button><CommentMenuPortal anchorRef={moreBtnRef} open={menuOpen} onClose={() => setMenuOpen(false)} canEdit={comment.can_edit} canDelete={comment.can_delete} busy={busy} onEdit={() => { setMenuOpen(false); onEdit(comment) }} onRemove={() => { setMenuOpen(false); remove() }} onReport={() => { setMenuOpen(false); onReport?.('comment', comment.id) }} /></div></div></nav>}
      {!embedded && <RepliesBar replies={directReplies} expanded={expanded} setExpanded={setExpanded} onJump={jump} />}
    </div>
  </article>
}

function CommentList({ comments = [], onReply, onEdit, onDelete, onReport, onJump }) {
  const [visible, setVisible] = useState(20)
  const sentinelRef = useRef(null)
  const repliesByParent = useMemo(() => {
    const map = new Map()
    for (const c of comments) {
      if (!c.reply_to_comment_id) continue
      const key = Number(c.reply_to_comment_id)
      if (!map.has(key)) map.set(key, [])
      map.get(key).push(c)
    }
    return map
  }, [comments])
  useEffect(() => { setVisible(20) }, [comments.length])
  useEffect(() => {
    const el = sentinelRef.current
    if (!el) return
    const io = new IntersectionObserver(entries => { if (entries[0]?.isIntersecting) setVisible(v => Math.min(comments.length, v + 20)) }, { rootMargin: '240px' })
    io.observe(el)
    return () => io.disconnect()
  }, [comments.length])
  if (!comments.length) return <div className="empty-state"><i className="fas fa-comment-dots" /><p>暂无回复，来说点什么吧</p></div>
  return <div className="comment-list">{comments.slice(0, visible).map(c => <CommentCard key={c.id} comment={c} onReply={onReply} onEdit={onEdit} onDelete={onDelete} onReport={onReport} directReplies={repliesByParent.get(Number(c.id)) || []} onJump={onJump} />)}{visible < comments.length && <div ref={sentinelRef} className="infinite-loader">正在加载更多回复...</div>}</div>
}

function CommentEditor({ me, mode = 'reply', editingComment, content, setContent, replyingTo, onCancelReply, onCancelEdit, onJump, onSubmit, sending, err, onTyping, onTypingEnd }) {
  const [preview, setPreview] = useState(false)
  const trimmedLength = content.trim().length
  const minLength = 16
  const tooShort = trimmedLength > 0 && trimmedLength < minLength
  if (!me) return <div className="comment-login"><p>登录后即可发表回复</p><a className="btn btn-primary" href="/login"><i className="fas fa-right-to-bracket" /> 去登录</a></div>
  return <form className="comment-editor" onSubmit={onSubmit}>
    {err && <div className="alert alert-error">{err}</div>}
    {mode === 'reply' && <ReplyIndicator comment={replyingTo} onCancel={onCancelReply} onJump={onJump} />}
    {mode === 'edit' && <div className="reply-indicator edit-mode-indicator"><span><i className="fas fa-pen" /> 正在编辑评论 #{editingComment?.id}</span>{onCancelEdit && <button type="button" className="reply-cancel" onClick={onCancelEdit}>取消编辑</button>}</div>}
    <div className="editor-toolbar"><span><i className="fab fa-markdown" /> 支持 Markdown</span><button type="button" onClick={() => setPreview(!preview)}>{preview ? '继续编辑' : '实时预览'}</button></div>
    {preview ? <div className="editor-preview"><MarkdownRenderer content={content || '预览会显示在这里'} compact /></div> : <textarea className="form-textarea comment-textarea" required minLength={minLength} maxLength={2000} value={content} onChange={e => { setContent(e.target.value); onTyping?.() }} onBlur={() => onTypingEnd?.()} onKeyDown={e => { if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') onSubmit(e) }} placeholder={mode === 'edit' ? '编辑评论，至少 16 个字，Ctrl + Enter 保存' : replyingTo ? `回复 @${replyingTo.author}，至少 16 个字，Ctrl + Enter 发送` : '写下你的回复，至少 16 个字，Ctrl + Enter 发送'} />}
    {tooShort && <div className="editor-minlength-hint"><i className="fas fa-circle-info" /> 还差 {minLength - trimmedLength} 个字，评论至少需要 {minLength} 个字</div>}
    <div className="editor-actions"><span className={tooShort ? 'too-short' : ''}>{content.length}/2000 · 最少 {minLength} 字</span><button className="btn btn-primary" disabled={sending || trimmedLength < minLength}><i className={`fas ${sending ? 'fa-spinner fa-spin' : 'fa-paper-plane'}`} /> {sending ? '处理中' : mode === 'edit' ? '保存修改' : '发表回复'}</button></div>
  </form>
}

function PostDetail({ id, me }) {
  const [data, setData] = useState(null)
  const [content, setContent] = useState('')
  const [replyingTo, setReplyingTo] = useState(null)
  const [editingComment, setEditingComment] = useState(null)
  const [composerMode, setComposerMode] = useState('reply')
  const [err, setErr] = useState('')
  const [sending, setSending] = useState(false)
  const [replyStatus, setReplyStatus] = useState('hidden')
  const [detailReady, setDetailReady] = useState(false)
  const [postMenuOpen, setPostMenuOpen] = useState(false)
  const postMoreBtnRef = useRef(null)
  const load = (silent = false) => api(`/api/posts/${id}`).then(d => { setData(d); updateSeo({ title: `${d.post.title} - 泓聊社区`, description: textExcerpt(d.post.content || d.post.preview || ''), url: absoluteUrl(`/post/${id}`), image: absoluteUrl('/favicon.svg'), type: 'article' }) }).catch(e => { if (!silent) setErr(e.message) })
  const handleTopicEvent = useMemo(() => msg => {
    if (!msg?.type?.startsWith('comment_')) return
    setData(old => {
      if (!old) return old
      if (msg.type === 'comment_created' && msg.comment) {
        if (old.comments?.some(c => c.id === msg.comment.id)) return old
        return { ...old, comments: [...(old.comments || []), msg.comment], post: { ...old.post, comments: Number(old.post.comments || 0) + 1 } }
      }
      if (msg.type === 'comment_updated' && msg.comment) return { ...old, comments: (old.comments || []).map(c => c.id === msg.comment.id ? msg.comment : c) }
      if (msg.type === 'comment_deleted') {
        if (msg.visible && msg.comment) return { ...old, comments: (old.comments || []).map(c => c.id === msg.comment.id ? msg.comment : c) }
        return { ...old, comments: (old.comments || []).filter(c => c.id !== msg.comment_id), post: { ...old.post, comments: Math.max(0, Number(old.post.comments || 0) - 1) } }
      }
      return old
    })
  }, [id])
  const { presence, sendTyping, sendTypingEnd, sendEditing, sendEditingEnd } = useTopicPresence(id, me, handleTopicEvent)
  const draftKey = editingComment ? `yhdet_edit_draft_${editingComment.id}` : ''
  useEffect(() => {
    if (composerMode === 'edit' && editingComment?.id) sendEditing(editingComment.id)
    return () => { if (editingComment?.id) sendEditingEnd(editingComment.id) }
  }, [composerMode, editingComment?.id])
  useEffect(() => {
    if (composerMode === 'edit' && draftKey) localStorage.setItem(draftKey, content)
  }, [composerMode, draftKey, content])
  useEffect(() => { let alive = true; setData(null); setDetailReady(false); setErr(''); setReplyingTo(null); setEditingComment(null); setComposerMode('reply'); setReplyStatus('hidden'); const started = Date.now(); api(`/api/posts/${id}`).then(d => { if (!alive) return; const wait = Math.max(260 - (Date.now() - started), 0); setTimeout(() => { if (alive) { setData(d); setDetailReady(true); updateSeo({ title: `${d.post.title} - 泓聊社区`, description: textExcerpt(d.post.content || d.post.preview || ''), url: absoluteUrl(`/post/${id}`), image: absoluteUrl('/favicon.svg'), type: 'article' }) } }, wait) }).catch(e => alive && setErr(e.message)); return () => { alive = false } }, [id])
  function highlightComment(commentId) {
    const el = document.getElementById(`comment-${commentId}`)
    if (!el) return
    history.replaceState(null, '', `#comment-${commentId}`)
    el.classList.remove('comment-focus')
    void el.offsetWidth
    el.classList.add('comment-focus')
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    setTimeout(() => el.classList.remove('comment-focus'), 2200)
  }
  function startReply(comment = null) {
    if (comment?.quote_only && comment.jump_to_id) return highlightComment(comment.jump_to_id)
    if (!me) {
      setComposerMode('reply')
      setEditingComment(null)
      setReplyingTo(comment)
      setContent('')
      setReplyStatus('expanded')
      return
    }
    if (composerMode === 'edit' && content !== (editingComment?.content || '') && !confirm('当前编辑内容还没保存，确定切换到回复吗？')) return
    setComposerMode('reply'); setEditingComment(null); setReplyingTo(comment); setContent(''); setReplyStatus('expanded')
  }
  function startEdit(comment) {
    if (!me) return navigate('/login')
    if (comment.deleted) return notify('已删除的评论不能编辑', 'error')
    if (composerMode === 'edit' && editingComment?.id !== comment.id && content !== (editingComment?.content || '') && !confirm('当前编辑内容还没保存，确定切换到另一条评论吗？')) return
    setComposerMode('edit'); setReplyingTo(null); setEditingComment(comment); setReplyStatus('expanded')
    setContent(localStorage.getItem(`yhdet_edit_draft_${comment.id}`) || comment.content || '')
  }
  function collapseReplyConsole() {
    sendTypingEnd()
    if (editingComment?.id) sendEditingEnd(editingComment.id)
    setReplyStatus('collapsed')
  }
  function closeReplyConsole() {
    sendTypingEnd()
    if (editingComment?.id) sendEditingEnd(editingComment.id)
    setReplyStatus('hidden')
    setReplyingTo(null)
    setEditingComment(null)
    setComposerMode('reply')
    setContent('')
  }
  function sharePost() {
    setPostMenuOpen(false)
    copyText(absoluteUrl(`/post/${id}`), '帖子链接已复制')
  }
  async function reportContent(targetType, targetId) {
    if (!me) return navigate('/login')
    const reason = prompt('举报原因（例如：广告、辱骂、违法、隐私泄露）', '违规内容')
    if (!reason?.trim()) return
    const detail = prompt('补充说明（可选）', '') || ''
    try {
      await api('/api/reports', { method:'POST', body: JSON.stringify({ target_type: targetType, target_id: Number(targetId), reason: reason.trim(), detail: detail.trim() }) })
      notify('已提交举报，管理员会尽快处理', 'success')
    } catch (e) { notify(e.message, 'error') }
  }
  useEffect(() => {
    if (!data || !location.hash.startsWith('#comment-')) return
    const targetId = location.hash.replace('#comment-', '')
    setTimeout(() => highlightComment(targetId), 80)
  }, [data?.comments?.length])
  async function saveEditComment() {
    if (!editingComment) return
    const nextContent = content.trim()
    if (!nextContent) return setErr('评论内容不能为空')
    if (nextContent.length < 16) return setErr('评论至少需要 16 个字')
    setSending(true); setErr('')
    try {
      const r = await api(`/api/posts/${id}/comments/${editingComment.id}`, { method: 'PATCH', body: JSON.stringify({ content: nextContent, reply_to_comment_id: editingComment.reply_to_comment_id || null }) })
      localStorage.removeItem(`yhdet_edit_draft_${editingComment.id}`)
      sendEditingEnd(editingComment.id)
      const editedId = editingComment.id
      if (r.comment) setData(d => d ? { ...d, comments: (d.comments || []).map(c => c.id === r.comment.id ? r.comment : c) } : d)
      setContent(''); setEditingComment(null); setComposerMode('reply'); setReplyStatus('hidden'); notify('修改已保存', 'success'); setTimeout(() => highlightComment(editedId), 80)
    } catch (e) { setErr(e.message); notify(e.message, 'error') } finally { setSending(false) }
  }
  async function deleteComment(comment) {
    setErr('')
    try {
      const r = await api(`/api/posts/${id}/comments/${comment.id}`, { method: 'DELETE' })
      setData(d => {
        if (!d) return d
        if (r.visible && r.comment) return { ...d, comments: (d.comments || []).map(c => c.id === r.comment.id ? r.comment : c) }
        return { ...d, comments: (d.comments || []).filter(c => c.id !== comment.id), post: { ...d.post, comments: Math.max(0, Number(d.post.comments || 0) - 1) } }
      })
    } catch (e) { setErr(e.message); notify(e.message, 'error'); throw e }
  }
  async function comment(e) {
    e.preventDefault(); setErr('')
    if (composerMode === 'edit') return saveEditComment()
    if (!content.trim()) return setErr('评论内容不能为空')
    if (content.trim().length < 16) return setErr('评论至少需要 16 个字')
    setSending(true)
    try {
      const r = await api(`/api/posts/${id}/comments`, { method: 'POST', body: JSON.stringify({ content: content.trim(), reply_to_comment_id: replyingTo?.id || null }) })
      sendTypingEnd()
      const newComment = r.comment
      if (newComment) setData(d => d ? { ...d, comments: [...(d.comments || []).filter(c => c.id !== newComment.id), newComment], post: { ...d.post, comments: r.comment_count ?? Number(d.post.comments || 0) + 1 } } : d)
      if (r.current_points !== undefined) mergeStoredUser({ available_points: r.current_points })
      setContent(''); setReplyingTo(null); setReplyStatus('hidden'); notify('回复已发表', 'success'); history.replaceState(null, '', location.pathname)
    } catch (e) { setErr(e.message); notify(e.message, 'error') } finally { setSending(false) }
  }
  if (err && !data) return <><PageChrome /><div className="main-content"><div className="alert alert-error">{err}</div></div></>
  if (!data || !detailReady) return <TopicDotLoader />
  const p = data.post
  return <><PageChrome /><div className="main-content"><div className="detail-wrap">
    <div className="card animate-fadeInUp post-detail-card">
      <div className="card-header post-detail-header">
        <h2>{p.title}</h2>
        <div className="post-meta detail-meta">
          <div className="post-author">
            <AvatarRing user={p} src={p.avatar} size={48} className="post-avatar-ring" />
            <a className={`post-author-name ${usernameClass(p)}`} href={`/user/${p.user_id}`}>{p.author}</a><UsernameBadge user={p} />
            {p.role ? <span className="role-badge role-super-admin"><i className="fas fa-crown" /> {p.role.includes('超级') ? p.role : p.role === '超管' ? '超级管理员' : p.role}</span> : <span className="role-badge role-user"><i className="fas fa-user" /> 用户</span>}
          </div>
          {p.custom_title && <span className="custom-title">{p.custom_title}</span>}
          <div className="post-meta-item"><i className="far fa-clock" /> {relativeTime(p.time)}</div>
          <div className="post-meta-item detail-counts"><i className="far fa-comment" /> {data.comments.length || ''}<span className="meta-split">|</span><i className="far fa-eye" /> {p.views || ''}</div>
        </div>
      </div>
      <div className="card-body"><MarkdownRenderer content={p.content} /></div>
      <div className="main-post-controls">
        <button type="button" className="main-post-reply-trigger reply create" title={me ? '回复楼主' : '登录后回复'} aria-label={me ? '回复楼主' : '登录后回复'} onClick={() => startReply(null)}><i className="fas fa-reply" /></button>
        <button ref={postMoreBtnRef} type="button" className="main-post-more-trigger more-toggle" title="更多" aria-label="更多" aria-expanded={postMenuOpen} onClick={() => setPostMenuOpen(v => !v)}><i className="fas fa-ellipsis" /></button>
        <PostMoreMenuPortal anchorRef={postMoreBtnRef} open={postMenuOpen} onClose={() => setPostMenuOpen(false)} onShare={sharePost} onReport={() => { setPostMenuOpen(false); reportContent('post', p.id) }} />
      </div>
    </div>

    <section className="card animate-fadeInUp reply-card forum-comments" style={{ animationDelay: '0.1s' }}>
      <div className="card-header comments-header"><div className="comments-title-row"><h3><i className="fas fa-comments" style={{ color: 'var(--primary)' }} /> 评论 <span>{data.comments.length}</span></h3><PresenceBar presence={presence} /></div><PresenceActivity presence={presence} /></div>
      <CommentList comments={sortCommentsForDisplay(data.comments)} onReply={startReply} onEdit={startEdit} onDelete={deleteComment} onReport={reportContent} onJump={highlightComment} />
    </section>

    {replyStatus !== 'hidden' && createPortal(
      <div className={`floating-reply-console ${replyStatus}`}>
        {replyStatus === 'collapsed' ? <button type="button" className="reply-capsule" onClick={() => setReplyStatus('expanded')}>
          <span className="reply-breathing-dot" />
          <span className="reply-capsule-text">对 <b>@{composerMode === 'edit' ? `评论 #${editingComment?.id}` : replyingTo?.author || p.author || '楼主'}</b> 的回复已收起...</span>
          <span className="reply-capsule-action">点击展开 <i className="fas fa-chevron-up" /></span>
        </button> : <div className="floating-reply-panel">
          <div className="floating-reply-head"><div><span>当前回复目标</span><strong>{composerMode === 'edit' ? `编辑评论 #${editingComment?.id}` : replyingTo ? `正在回复 @${replyingTo.author}` : `正在回复 @${p.author || '楼主'}`}</strong></div><div className="floating-reply-actions"><button type="button" title="收起" aria-label="收起" onClick={collapseReplyConsole}><i className="fas fa-chevron-down" /></button><button type="button" title="关闭" aria-label="关闭" onClick={closeReplyConsole}><i className="fas fa-xmark" /></button></div></div>
          <div className="floating-reply-body">{replyingTo?.deleted && <div className="reply-deleted-note">你正在回复的评论已被删除。</div>}<CommentEditor me={me} mode={composerMode} editingComment={editingComment} content={content} setContent={setContent} replyingTo={replyingTo} onCancelReply={() => setReplyingTo(null)} onJump={highlightComment} onSubmit={comment} sending={sending} err={err} onTyping={sendTyping} onTypingEnd={sendTypingEnd} onCancelEdit={() => { if (editingComment?.id) sendEditingEnd(editingComment.id); setEditingComment(null); setComposerMode('reply'); setContent('') }} /></div>
        </div>}
      </div>, document.body)}

    <div className="back-home"><a className="btn btn-secondary" href="/"><i className="fas fa-arrow-left" /> 返回首页</a></div>
  </div></div></>
}

function AvatarUploader({ onDone }) {
  const [open, setOpen] = useState(false)
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState('')
  const [busy, setBusy] = useState(false)
  const [ready, setReady] = useState(false)
  const [scale, setScale] = useState(1)
  const [offset, setOffset] = useState({ x: 0, y: 0 })
  const imgRef = useRef(null)
  const stageRef = useRef(null)
  const dragRef = useRef(null)
  const cropSize = 220
  const stageSize = 280
  const cropLeft = (stageSize - cropSize) / 2
  const cropTop = (stageSize - cropSize) / 2

  const getContainSize = () => {
    const img = imgRef.current
    if (!img?.naturalWidth || !img?.naturalHeight) return { width: stageSize, height: stageSize }
    const ratio = Math.min(stageSize / img.naturalWidth, stageSize / img.naturalHeight)
    return { width: img.naturalWidth * ratio, height: img.naturalHeight * ratio }
  }
  const minScaleFor = (base = getContainSize()) => Math.max(1, cropSize / Math.max(1, base.width), cropSize / Math.max(1, base.height))
  const maxScaleFor = (base = getContainSize()) => Math.max(3, minScaleFor(base) * 3)
  const clampOffset = (next, nextScale = scale) => {
    const base = getContainSize()
    const safeScale = Math.min(maxScaleFor(base), Math.max(minScaleFor(base), Number(nextScale) || 1))
    const w = base.width * safeScale
    const h = base.height * safeScale
    const minX = cropLeft + cropSize - w
    const maxX = cropLeft
    const minY = cropTop + cropSize - h
    const maxY = cropTop
    return {
      x: Math.min(maxX, Math.max(minX, next.x)),
      y: Math.min(maxY, Math.max(minY, next.y)),
    }
  }
  const fitImage = () => {
    setReady(true)
    const base = getContainSize()
    const initialScale = minScaleFor(base)
    setScale(initialScale)
    setOffset(clampOffset({ x: (stageSize - base.width * initialScale) / 2, y: (stageSize - base.height * initialScale) / 2 }, initialScale))
  }
  const pick = f => {
    if (!f) return
    if (!String(f.type || '').startsWith('image/')) return notify('请选择图片文件', 'error')
    if (preview) URL.revokeObjectURL(preview)
    setFile(f)
    setReady(false)
    setPreview(URL.createObjectURL(f))
    setScale(1)
    setOffset({ x: 0, y: 0 })
  }
  const setZoom = value => {
    const base = getContainSize()
    const nextScale = Math.min(maxScaleFor(base), Math.max(minScaleFor(base), Number(value) || 1))
    const centerX = cropLeft + cropSize / 2
    const centerY = cropTop + cropSize / 2
    const oldScale = Math.max(minScaleFor(base), scale || 1)
    const next = {
      x: centerX - (centerX - offset.x) * (nextScale / oldScale),
      y: centerY - (centerY - offset.y) * (nextScale / oldScale),
    }
    setScale(nextScale)
    setOffset(clampOffset(next, nextScale))
  }
  const point = e => {
    const t = e.touches?.[0] || e.changedTouches?.[0] || e
    return { x: t.clientX, y: t.clientY }
  }
  const startDrag = e => {
    if (!preview || busy) return
    e.preventDefault()
    const p = point(e)
    dragRef.current = { x: p.x, y: p.y, start: offset }
    window.addEventListener('mousemove', moveDrag, { passive: false })
    window.addEventListener('mouseup', endDrag)
    window.addEventListener('touchmove', moveDrag, { passive: false })
    window.addEventListener('touchend', endDrag)
  }
  const moveDrag = e => {
    const d = dragRef.current
    if (!d) return
    e.preventDefault()
    const p = point(e)
    setOffset(clampOffset({ x: d.start.x + p.x - d.x, y: d.start.y + p.y - d.y }))
  }
  const endDrag = () => {
    dragRef.current = null
    window.removeEventListener('mousemove', moveDrag)
    window.removeEventListener('mouseup', endDrag)
    window.removeEventListener('touchmove', moveDrag)
    window.removeEventListener('touchend', endDrag)
  }
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); endDrag() }, [preview])

  function cropParams() {
    const img = imgRef.current
    if (!img?.naturalWidth || !img?.naturalHeight) throw new Error('图片尚未加载完成')
    const base = getContainSize()
    const renderedW = base.width * scale
    const renderedH = base.height * scale
    const x = (cropLeft - offset.x) / renderedW * img.naturalWidth
    const y = (cropTop - offset.y) / renderedH * img.naturalHeight
    const width = cropSize / renderedW * img.naturalWidth
    const height = cropSize / renderedH * img.naturalHeight
    const safeX = Math.max(0, Math.min(img.naturalWidth - 1, x))
    const safeY = Math.max(0, Math.min(img.naturalHeight - 1, y))
    return {
      x: Math.round(safeX),
      y: Math.round(safeY),
      width: Math.round(Math.min(width, img.naturalWidth - safeX)),
      height: Math.round(Math.min(height, img.naturalHeight - safeY)),
    }
  }
  async function upload() {
    if (!file) return notify('请先选择头像', 'error')
    setBusy(true)
    try {
      const c = cropParams()
      const fd = new FormData()
      fd.append('file', file, file.name || 'avatar.png')
      fd.append('x', String(c.x))
      fd.append('y', String(c.y))
      fd.append('width', String(c.width))
      fd.append('height', String(c.height))
      const res = await api('/api/me/avatar', { method:'POST', body: fd })
      localStorage.setItem('yhdet_user', JSON.stringify(res.user)); notify('头像已更新', 'success'); setOpen(false); onDone?.(res.user)
    }
    catch(e) { notify(e.message, 'error') } finally { setBusy(false) }
  }
  const base = ready ? getContainSize() : { width: stageSize, height: stageSize }
  const minZoom = ready ? minScaleFor(base) : 1
  const maxZoom = ready ? maxScaleFor(base) : 3
  const imageStyle = {
    width: base.width, height: base.height,
    transform: `translate3d(${offset.x}px, ${offset.y}px, 0) scale(${scale})`,
  }
  const modal = open ? createPortal(
    <div className="modal-mask full-avatar-mask global-avatar-crop-layer" onClick={() => setOpen(false)}><div className="avatar-modal avatar-crop-modal" onClick={e => e.stopPropagation()}><h3><i className="fas fa-crop-simple" /> 上传并裁剪头像</h3><div className="drop-zone" onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); pick(e.dataTransfer.files?.[0]) }}><input type="file" accept="image/*" onChange={e => pick(e.target.files?.[0])} /><p>点击选择或拖入图片</p><small>拖动图片调整位置，用滑块缩放；保存时由后端按原图像素裁剪</small></div>{preview && <div ref={stageRef} className="crop-stage" onMouseDown={startDrag} onTouchStart={startDrag}><img ref={imgRef} className="crop-image" src={preview} alt="裁剪" onLoad={fitImage} draggable="false" style={imageStyle} /><div className="crop-dim crop-dim-top" /><div className="crop-dim crop-dim-bottom" /><div className="crop-dim crop-dim-left" /><div className="crop-dim crop-dim-right" /><div className="crop-box" /></div>}{preview && <div className="crop-controls single"><label>缩放 <input type="range" min={minZoom} max={maxZoom} step="0.01" value={Math.max(minZoom, Math.min(maxZoom, scale))} onChange={e => setZoom(e.target.value)} /></label></div>}<div className="admin-actions"><button className="btn btn-primary" disabled={busy || !file || !ready} onClick={upload}>{busy ? '上传中' : '确认上传'}</button><button className="btn btn-secondary" onClick={() => setOpen(false)}>取消</button></div></div></div>,
    document.body
  ) : null
  return <>
    <button className="avatar-edit-btn" onClick={() => setOpen(true)} title="编辑头像"><i className="fas fa-pen" /></button>
    {modal}
  </>
}

function UserPage({ id, me, setMe }) {
  const [data, setData] = useState(null)
  const [postsPage, setPostsPage] = useState(1)
  const [commentsPage, setCommentsPage] = useState(1)
  const [sentCommentsPage, setSentCommentsPage] = useState(1)
  const [ordersPage, setOrdersPage] = useState(1)
  const [loadingPosts, setLoadingPosts] = useState(false)
  const [loadingComments, setLoadingComments] = useState(false)
  const [loadingSentComments, setLoadingSentComments] = useState(false)
  const [loadingOrders, setLoadingOrders] = useState(false)
  const [showPosts, setShowPosts] = useState(false)
  const [showComments, setShowComments] = useState(false)
  const [showSentComments, setShowSentComments] = useState(false)
  const [showOrders, setShowOrders] = useState(false)
  const isMe = me && String(me.id) === String(id)
  const fetchUser = (pp = 1, cp = 1, scp = 1, op = 1) => api(`/api/users/${id}?posts_page=${pp}&comments_page=${cp}&sent_comments_page=${scp}&orders_page=${op}&page_size=10`)
  useEffect(() => { let alive = true; setData(null); setPostsPage(1); setCommentsPage(1); setSentCommentsPage(1); setOrdersPage(1); setShowPosts(false); setShowComments(false); setShowSentComments(false); setShowOrders(false); fetchUser(1,1,1,1).then(d => { if (alive) { setData(d); document.title = `${d.user.username} 的主页 - 泓聊社区`; if (location.hash === '#comments') setShowComments(true) } }); return () => { alive = false } }, [id])
  useEffect(() => { if (!isMe) return; const t = setInterval(() => fetchUser(1,1,1,1).then(d => setData(old => old ? { ...old, unread_notifications: d.unread_notifications } : d)).catch(()=>{}), 5000); return () => clearInterval(t) }, [id, isMe])
  if (!data) return <DetailSkeleton />
  const u = data.user
  const avatarDone = user => { setMe?.(user); setData(d => ({ ...d, user })); }
  function handleOrderChanged(res, changedOrder) {
    if (res.user) setMe?.(res.user)
    setData(d => {
      if (!d) return d
      const nextUser = res.user ? { ...d.user, ...res.user } : d.user
      const refreshed = Array.isArray(res.orders) ? res.orders : null
      if (refreshed) {
        const byId = new Map(refreshed.map(o => [o.id, o]))
        return { ...d, user: nextUser, market_orders: (d.market_orders || []).map(o => byId.get(o.id) || (res.order?.id === o.id ? { ...o, ...res.order } : o)) }
      }
      return { ...d, user: nextUser, market_orders: (d.market_orders || []).map(o => o.id === changedOrder.id ? { ...o, ...(res.order || {}), is_equipped: !changedOrder.is_equipped } : (o.item_type && o.item_type === changedOrder.item_type ? { ...o, is_equipped: false } : o)) }
    })
  }
  async function morePosts() {
    if (!data.posts_has_more || loadingPosts) return
    setLoadingPosts(true)
    try { const np = postsPage + 1; const d = await fetchUser(np, commentsPage, sentCommentsPage, ordersPage); setPostsPage(np); setData(old => ({ ...d, posts: [...(old?.posts || []), ...(d.posts || [])], received_comments: old?.received_comments || d.received_comments, sent_comments: old?.sent_comments || d.sent_comments, market_orders: old?.market_orders || d.market_orders })) } finally { setLoadingPosts(false) }
  }
  async function moreComments() {
    if (!data.received_comments_has_more || loadingComments) return
    setLoadingComments(true)
    try { const np = commentsPage + 1; const d = await fetchUser(postsPage, np, sentCommentsPage, ordersPage); setCommentsPage(np); setData(old => ({ ...d, posts: old?.posts || d.posts, received_comments: [...(old?.received_comments || []), ...(d.received_comments || [])], sent_comments: old?.sent_comments || d.sent_comments, market_orders: old?.market_orders || d.market_orders })) } finally { setLoadingComments(false) }
  }
  async function moreSentComments() {
    if (!data.sent_comments_has_more || loadingSentComments) return
    setLoadingSentComments(true)
    try { const np = sentCommentsPage + 1; const d = await fetchUser(postsPage, commentsPage, np, ordersPage); setSentCommentsPage(np); setData(old => ({ ...d, posts: old?.posts || d.posts, received_comments: old?.received_comments || d.received_comments, sent_comments: [...(old?.sent_comments || []), ...(d.sent_comments || [])], market_orders: old?.market_orders || d.market_orders })) } finally { setLoadingSentComments(false) }
  }
  async function moreOrders() {
    if (!data.market_orders_has_more || loadingOrders) return
    setLoadingOrders(true)
    try { const np = ordersPage + 1; const d = await fetchUser(postsPage, commentsPage, sentCommentsPage, np); setOrdersPage(np); setData(old => ({ ...d, posts: old?.posts || d.posts, received_comments: old?.received_comments || d.received_comments, sent_comments: old?.sent_comments || d.sent_comments, market_orders: [...(old?.market_orders || []), ...(d.market_orders || [])] })) } finally { setLoadingOrders(false) }
  }
  async function readOne(c) {
    if (!isMe || !c.notification_id || c.read) return navigate(`/post/${c.post_id}#comment-${c.id}`)
    try {
      const res = await api(`/api/me/notifications/${c.notification_id}/read`, { method:'POST' })
      setData(d => ({ ...d, unread_notifications: res.unread ?? Math.max(0, (d.unread_notifications || 0)-1), received_comments: d.received_comments.map(x => x.id === c.id ? { ...x, read: true } : x) }))
      window.dispatchEvent(new Event('notifications:refresh'))
    } finally { navigate(`/post/${c.post_id}#comment-${c.id}`) }
  }
  async function readAll() {
    if (!isMe) return
    const res = await api('/api/me/notifications/read', { method:'POST', body: JSON.stringify({}) })
    setData(d => ({ ...d, unread_notifications: res.unread || 0, received_comments: d.received_comments.map(x => ({ ...x, read: true })) }))
    window.dispatchEvent(new Event('notifications:refresh'))
  }
  return <><PageChrome /><div className="main-content"><div className="detail-wrap">
    <div className={`card animate-fadeInUp user-profile-card ${profileThemeClass(u)}`}>
      <div className="card-body user-profile-body"><div className="profile-head-row"><div className="avatar-wrap"><AvatarRing user={u} src={u.avatar} size={108} className="profile-avatar-ring" />{isMe && <AvatarUploader onDone={avatarDone} />}</div><div className="profile-title-block"><h2 className={`profile-name-with-badge ${usernameClass(u)}`}>{u.username}<UsernameBadge user={u} /></h2><div className="profile-badges">{u.role_label ? <span className="role-badge role-super-admin"><i className="fas fa-crown" /> {u.role_label}</span> : <span className="role-badge role-user"><i className="fas fa-user" /> 用户</span>}{u.custom_title && <span className="custom-title">{u.custom_title}</span>}</div></div></div><ProfileStats stats={data.profile_stats} /></div>
    </div>
    <div className="card animate-fadeInUp"><div className="card-header fold-head"><h3><i className="fas fa-pen-nib" style={{ color: 'var(--primary)' }} /> TA 的帖子 <span className="mini-busy">{data.posts_total || 0}</span></h3><button className="btn btn-sm btn-secondary" onClick={() => setShowPosts(!showPosts)}>{showPosts ? '折叠' : '展开'}</button></div>{showPosts && <div>{data.posts.length ? data.posts.map(p => <PostItem key={p.id} post={p} innerRef={postFlipRef(p.id)} />) : <div className="empty-state"><i className="fas fa-feather-pointed" /><p>TA 还没有发表过帖子</p></div>}{data.posts_has_more && <div className="infinite-loader"><button className="btn btn-sm btn-secondary" onClick={morePosts} disabled={loadingPosts}>{loadingPosts ? '加载中...' : '加载更多帖子'}</button></div>}</div>}</div>
    {isMe && <div className="card animate-fadeInUp" style={{ animationDelay: '0.08s' }}><div className="card-header fold-head"><h3><i className="fas fa-receipt" style={{ color: '#f59e0b' }} /> 我的兑换记录 <span className="mini-busy">{data.market_orders_total || 0}</span></h3><button className="btn btn-sm btn-secondary" onClick={() => setShowOrders(!showOrders)}>{showOrders ? '折叠' : '展开'}</button></div>{showOrders && <div>{data.market_orders?.length ? data.market_orders.map(o => <OrderRow order={o} key={o.id} onChanged={handleOrderChanged} />) : <div className="empty-state"><i className="fas fa-receipt" /><p>{me ? '暂无兑换记录' : '登录后查看个人兑换记录'}</p></div>}{data.market_orders_has_more && <div className="infinite-loader"><button className="btn btn-sm btn-secondary" onClick={moreOrders} disabled={loadingOrders}>{loadingOrders ? '加载中...' : '加载更多兑换记录'}</button></div>}</div>}</div>}
    {isMe && <div className="card animate-fadeInUp" style={{ animationDelay: '0.1s' }}><div className="card-header fold-head"><h3><i className="fas fa-message" style={{ color: 'var(--secondary)' }} /> 被评论消息 {data.unread_notifications > 0 && <span className="bubble-badge red-badge inline-bubble">{data.unread_notifications > 99 ? '99+' : data.unread_notifications}</span>}</h3><div className="admin-actions">{data.unread_notifications > 0 && <button className="btn btn-sm btn-secondary" onClick={readAll}>全部已读</button>}<button className="btn btn-sm btn-secondary" onClick={() => setShowComments(!showComments)}>{showComments ? '折叠' : '展开'}</button></div></div>{showComments && <div>{data.received_comments?.length ? data.received_comments.map(c => <button className={`post-item notification-row ${!c.read ? 'is-unread' : ''}`} onClick={() => readOne(c)} key={c.id}><div className="reply-row"><img className="post-avatar" src={safeAvatar(c.avatar)} onError={onAvatarError} /><div className="reply-main"><div className="reply-head"><b>{c.author} 评论了你的帖子</b><span>{relativeTime(c.time)}</span></div><div className="post-preview">《{c.post_title}》</div></div>{!c.read && <span className="unread-dot" />}</div></button>) : <div className="empty-state"><i className="fas fa-comment-slash" /><p>暂无被评论消息</p></div>}{data.received_comments_has_more && <div className="infinite-loader"><button className="btn btn-sm btn-secondary" onClick={moreComments} disabled={loadingComments}>{loadingComments ? '加载中...' : '加载更多评论'}</button></div>}</div>}</div>}
    {isMe && <div className="card animate-fadeInUp" style={{ animationDelay: '0.12s' }}><div className="card-header fold-head"><h3><i className="fas fa-paper-plane" style={{ color: '#16a34a' }} /> 我发出的评论 <span className="mini-busy">{data.sent_comments_total || 0}</span></h3><button className="btn btn-sm btn-secondary" onClick={() => setShowSentComments(!showSentComments)}>{showSentComments ? '折叠' : '展开'}</button></div>{showSentComments && <div>{data.sent_comments?.length ? data.sent_comments.map(c => <a className="post-item notification-row sent-comment-row" href={`/post/${c.post_id}#comment-${c.id}`} key={c.id}><div className="reply-row"><img className="post-avatar" src={safeAvatar(c.owner_avatar)} onError={onAvatarError} /><div className="reply-main"><div className="reply-head"><b>回复了 {c.owner_name} 的帖子</b><span>{relativeTime(c.time)}</span></div><div className="post-preview">《{c.post_title}》</div><div className="sent-comment-content">{c.content}</div></div></div></a>) : <div className="empty-state"><i className="fas fa-comment-dots" /><p>还没有发出过评论</p></div>}{data.sent_comments_has_more && <div className="infinite-loader"><button className="btn btn-sm btn-secondary" onClick={moreSentComments} disabled={loadingSentComments}>{loadingSentComments ? '加载中...' : '加载更多发出的评论'}</button></div>}</div>}</div>}
    <div className="back-home"><a className="btn btn-secondary" href="/"><i className="fas fa-arrow-left" /> 返回首页</a></div>
  </div></div></>
}

function SimpleSection({ type }) {
  const [data, setData] = useState(null)
  useEffect(() => { document.title = `${type === 'games' ? '小游戏' : '音乐'} - 泓聊社区`; api(`/api/${type}`).then(setData) }, [type])
  return <div className="main-content"><div className="card"><div className="card-header"><h3><i className={`fas ${type === 'games' ? 'fa-gamepad' : 'fa-music'}`} /> {type === 'games' ? '小游戏' : '音乐'}</h3></div><div className="card-body"><div className="alert alert-info">{data?.message || '加载中...'}</div><div className="user-grid">{data?.items?.map(x => <div className="user-card" key={x}><div className="empty-state" style={{ padding: 10 }}><i className={`fas ${type === 'games' ? 'fa-gamepad' : 'fa-music'}`} /><p>{x}</p></div></div>)}</div></div></div></div>
}


function AdminPage({ me }) {
  const tabs = [
    ['overview', '总览', 'fa-chart-line'],
    ['posts', '帖子', 'fa-file-lines'],
    ['comments', '评论', 'fa-comments'],
    ['reports', '举报', 'fa-flag'],
    ['users', '用户', 'fa-users'],
    ['announcements', '公告', 'fa-bullhorn'],
    ['donors', '捐赠者', 'fa-heart'],
    ['channels', '频道', 'fa-broadcast-tower'],
    ['market', '泓市场', 'fa-store'],
    ['settings', '系统设置', 'fa-gear'],
  ]
  const [tab, setTab] = useState('overview')
  const [data, setData] = useState({})
  const [q, setQ] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const [draft, setDraft] = useState({})
  useEffect(() => { document.title = '管理后台 - 泓聊社区' }, [])
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
  async function run(fn, opts = {}) {
    const { reload = true, apply } = opts
    setErr(''); setBusy(true)
    try {
      const res = await fn()
      if (apply) apply(res)
      notify('操作完成', 'success')
      if (reload) await load(tab)
      chromeCache = null; chromePromise = null
      return res
    }
    catch (e) { setErr(e.message); notify(e.message, 'error'); return null }
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
    {tab === 'reports' && <AdminReports items={items} run={run} load={load} />}
    {tab === 'users' && <AdminUsers items={items} run={run} />}
    {tab === 'announcements' && <AdminAnnouncements items={items} draft={draft} setDraft={setDraft} run={run} />}
    {tab === 'donors' && <AdminDonors items={items} draft={draft} setDraft={setDraft} run={run} />}
    {tab === 'channels' && <AdminChannels data={data.channels} draft={draft} setDraft={setDraft} run={run} />}
    {tab === 'market' && <AdminMarket data={data.market} setAdminData={setData} draft={draft} setDraft={setDraft} run={run} />}
    {tab === 'settings' && <AdminSettings data={data.settings} draft={draft} setDraft={setDraft} run={run} />} 
  </div>
}

function AdminOverview({ data }) {
  const stats = data?.stats || {}
  return <><div className="admin-stat-grid">
    <div className="admin-stat"><span>访问</span><b>{stats.visits || 0}</b></div><div className="admin-stat"><span>用户</span><b>{stats.users || 0}</b></div><div className="admin-stat"><span>帖子</span><b>{stats.posts || 0}</b></div><div className="admin-stat"><span>评论</span><b>{stats.comments || 0}</b></div>
  </div><div className="admin-grid"><div className="admin-card"><h3>最新帖子</h3>{data?.recent_posts?.map(p => <div className="admin-line" key={p.id}><span>{p.title}</span><a href={`/post/${p.id}`}>查看</a></div>)}</div><div className="admin-card"><h3>新用户</h3>{data?.recent_users?.map(u => <div className="admin-line" key={u.id}><span>{u.username}</span><span>{u.role === 'admin' ? '管理员' : '用户'}</span></div>)}</div></div></>
}
function AdminPosts({ items, run }) { return <div className="admin-card"><h3>帖子管理</h3>{items.map(p => <div className="admin-row" key={p.id}><div><b>{p.title}</b><p>{p.author} · {p.time} · 评论 {p.comments || 0} · 浏览 {p.views || 0}</p></div><div className="admin-actions"><button className="btn btn-sm btn-secondary" onClick={() => run(() => api(`/api/admin/posts/${p.id}`, { method:'PATCH', body: JSON.stringify({ pinned: !p.pinned }) }))}>{p.pinned ? '取消置顶' : '置顶'}</button><a className="btn btn-sm btn-secondary" href={`/post/${p.id}`}>查看</a><button className="btn btn-sm btn-danger" onClick={() => confirm('确定删除这个帖子及其评论？') && run(() => api(`/api/admin/posts/${p.id}`, { method:'DELETE' }))}>删除</button></div></div>)}</div> }
function AdminComments({ items, run }) { return <div className="admin-card"><h3>评论管理</h3>{items.map(c => <div className="admin-row" key={c.id}><div><b>{c.author}</b><p>{c.content}</p><small>来自《{c.post_title}》 · {relativeTime(c.created_at)}</small></div><div className="admin-actions"><a className="btn btn-sm btn-secondary" href={`/post/${c.post_id}`}>查看帖子</a><button className="btn btn-sm btn-danger" onClick={() => confirm('确定删除这条评论？') && run(() => api(`/api/admin/comments/${c.id}`, { method:'DELETE' }))}>删除</button></div></div>)}</div> }
function AdminReports({ items, run, load }) {
  const statusText = { open:'待处理', reviewing:'处理中', resolved:'已处理', rejected:'已驳回' }
  async function setStatus(r, status) {
    const note = status === 'rejected' ? (prompt('驳回原因/处理备注', '已查看，暂不处理') || '') : (prompt('处理备注（可留空）', '') || '')
    await run(() => api(`/api/admin/reports/${r.id}`, { method:'PATCH', body: JSON.stringify({ status, admin_note: note }) }))
  }
  return <div className="admin-card"><div className="admin-card-head"><h3><i className="fas fa-flag" /> 举报处理</h3><div className="admin-actions"><button className="btn btn-sm btn-secondary" onClick={() => load('reports')}>刷新</button></div></div>
    {!items.length && <div className="empty-state"><i className="fas fa-shield-check" /><p>暂无待处理举报</p></div>}
    {items.map(r => <div className="admin-row report-row" key={r.id}>
      <div><b>{r.target_type === 'post' ? '帖子' : '评论'}举报 #{r.id} <span className={`report-status ${r.status}`}>{statusText[r.status] || r.status}</span></b><p>{r.reason} · 举报人 {r.reporter} · 内容作者 {r.target_author || '未知'} · {relativeTime(r.created_at)}</p><small>来自《{r.post_title || '未知帖子'}》：{htmlText(r.target_preview || '').slice(0, 140)}</small>{r.detail && <small className="report-detail">补充：{r.detail}</small>}{r.admin_note && <small className="report-detail">处理备注：{r.admin_note}</small>}</div>
      <div className="admin-actions"><a className="btn btn-sm btn-secondary" href={`/post/${r.post_id}${r.target_type === 'comment' ? `#comment-${r.target_id}` : ''}`}>查看</a><button className="btn btn-sm btn-secondary" onClick={() => setStatus(r, 'reviewing')}>标记处理中</button><button className="btn btn-sm btn-secondary" onClick={() => setStatus(r, 'rejected')}>驳回</button><button className="btn btn-sm btn-danger" onClick={() => confirm('确认删除被举报内容并关闭举报？') && run(() => api(`/api/admin/reports/${r.id}/target`, { method:'DELETE' }))}>删除内容</button><button className="btn btn-sm btn-primary" onClick={() => setStatus(r, 'resolved')}>标记已处理</button></div>
    </div>)}
  </div>
}
function AdminUsers({ items, run }) {
  const [info, setInfo] = useState(null)
  const [loadingInfo, setLoadingInfo] = useState(false)
  async function openInfo(u) {
    setLoadingInfo(true)
    try { setInfo(await api(`/api/admin/users/${u.id}`)) }
    catch(e) { notify(e.message, 'error') }
    finally { setLoadingInfo(false) }
  }
  function freeze(u) {
    const days = prompt(`冻结 ${u.username} 多少天？`, '7')
    if (!days) return
    const reason = prompt('冻结原因（会用于邮件提示，可留空）', '') || ''
    run(() => api(`/api/admin/users/${u.id}/freeze`, { method:'POST', body: JSON.stringify({ days: Number(days), reason }) }))
  }
  function ban(u) {
    const reason = prompt(`永久封禁 ${u.username} 的原因？封号不可逆，会禁止邮箱/IP，并软删除账号。`, '') || ''
    if (!confirm(`确认永久封禁 ${u.username}？`)) return
    run(() => api(`/api/admin/users/${u.id}/ban`, { method:'POST', body: JSON.stringify({ reason }) }))
  }
  function hardDelete(u) {
    if (!confirm(`硬删除 ${u.username} 的测试数据？会删除帖子、评论、会话和账号，不能恢复。`)) return
    run(() => api(`/api/admin/users/${u.id}/hard-delete`, { method:'DELETE', body: JSON.stringify({ confirm:'DELETE' }) }))
  }
  return <div className="admin-card">
    <h3>用户管理</h3>
    {items.map(u => <div className="admin-row" key={u.id}>
      <div>
        <b>{u.username}</b>
        <p>{u.role === 'admin' ? '管理员' : '普通用户'} · {u.account_status === 'frozen' ? `冻结至 ${u.frozen_until}` : u.account_status === 'banned' ? '已封禁' : '正常'} · 帖子 {u.post_count || 0} · 评论 {u.comment_count || 0}</p>
        <small>{u.role_label || '无头衔'} {u.custom_title ? ` · ${u.custom_title}` : ''}</small>
      </div>
      <div className="admin-actions">
        <button className="btn btn-sm btn-secondary" onClick={() => openInfo(u)}>注册信息</button>
        <button className="btn btn-sm btn-secondary" onClick={() => run(() => api(`/api/admin/users/${u.id}`, { method:'PATCH', body: JSON.stringify({ role: u.role === 'admin' ? 'user' : 'admin', role_label: u.role === 'admin' ? '' : '超管', custom_title: u.role === 'admin' ? '' : '论坛主' }) }))}>{u.role === 'admin' ? '降为用户' : '设为管理员'}</button>
        {u.account_status === 'frozen' ? <button className="btn btn-sm btn-secondary" onClick={() => run(() => api(`/api/admin/users/${u.id}/unfreeze`, { method:'POST' }))}>解冻</button> : <button className="btn btn-sm btn-secondary" onClick={() => freeze(u)}>冻结</button>}
        <button className="btn btn-sm btn-danger" onClick={() => ban(u)}>封号</button>
        <button className="btn btn-sm btn-danger" onClick={() => hardDelete(u)}>硬删除</button>
        <a className="btn btn-sm btn-secondary" href={`/user/${u.id}`}>主页</a>
      </div>
    </div>)}
    {(info || loadingInfo) && <div className="modal-mask" onClick={() => setInfo(null)}>
      <div className="avatar-modal user-info-modal" onClick={e => e.stopPropagation()}>
        <h3><i className="fas fa-id-card" /> 用户注册信息</h3>
        {loadingInfo && <p>加载中...</p>}
        {info?.user && <div className="settings-grid">
          <label><span>用户名</span><input className="form-input" readOnly value={info.user.username || ''} /></label>
          <label><span>邮箱</span><input className="form-input" readOnly value={info.user.email || ''} /></label>
          <label><span>注册时间</span><input className="form-input" readOnly value={info.user.created_at || ''} /></label>
          <label><span>注册 IP</span><input className="form-input" readOnly value={info.user.register_ip || ''} /></label>
          <label><span>最后登录 IP</span><input className="form-input" readOnly value={info.user.last_login_ip || ''} /></label>
          <label><span>账号状态</span><input className="form-input" readOnly value={info.user.account_status || 'active'} /></label>
          <label className="settings-wide"><span>封禁原因</span><textarea className="form-textarea" readOnly value={info.user.ban_reason || ''} /></label>
        </div>}
        {info?.bans?.length > 0 && <div className="alert alert-info">封禁留档：{info.bans.map(b => `${b.banned_at} · ${b.ip || '无IP'} · ${b.reason || '无原因'}`).join(' / ')}</div>}
        <div className="admin-actions"><button className="btn btn-secondary" onClick={() => setInfo(null)}>关闭</button></div>
      </div>
    </div>}
  </div>
}
function AdminAnnouncements({ items, draft, setDraft, run }) { return <div className="admin-card"><h3>公告管理</h3><div className="admin-create"><input className="form-input" placeholder="新公告内容" value={draft.announcement || ''} onChange={e => setDraft({ ...draft, announcement: e.target.value })} /><button className="btn btn-primary" onClick={() => draft.announcement?.trim() && run(() => api('/api/admin/announcements', { method:'POST', body: JSON.stringify({ content: draft.announcement.trim() }) }).then(() => setDraft({ ...draft, announcement: '' })))}>发布公告</button></div>{items.map(a => <div className="admin-row" key={a.id}><div><b>{a.content}</b><p>{a.author} · {a.created_at}</p></div><button className="btn btn-sm btn-danger" onClick={() => confirm('确定删除公告？') && run(() => api(`/api/admin/announcements/${a.id}`, { method:'DELETE' }))}>删除</button></div>)}</div> }
function AdminDonors({ items, draft, setDraft, run }) { const d = draft.donor || {}; return <div className="admin-card"><h3>捐赠者管理</h3><div className="admin-create donor-create"><input className="form-input" placeholder="名称" value={d.name || ''} onChange={e => setDraft({ ...draft, donor: { ...d, name: e.target.value } })} /><input className="form-input" placeholder="金额，如 3元" value={d.amount || ''} onChange={e => setDraft({ ...draft, donor: { ...d, amount: e.target.value } })} /><input className="form-input" placeholder="日期，如 2026.6.29" value={d.donated_at || ''} onChange={e => setDraft({ ...draft, donor: { ...d, donated_at: e.target.value } })} /><button className="btn btn-primary" onClick={() => d.name?.trim() && d.amount?.trim() && d.donated_at?.trim() && run(() => api('/api/admin/donors', { method:'POST', body: JSON.stringify({ name: d.name.trim(), amount: d.amount.trim(), donated_at: d.donated_at.trim() }) }).then(() => setDraft({ ...draft, donor: {} })))}>添加</button></div>{items.map(x => <div className="admin-row" key={x.id}><div><b>{x.name}</b><p>{x.amount} · {x.donated_at}</p></div><button className="btn btn-sm btn-danger" onClick={() => confirm('确定删除捐赠记录？') && run(() => api(`/api/admin/donors/${x.id}`, { method:'DELETE' }))}>删除</button></div>)}</div> }

function AdminMarket({ data, setAdminData, draft, setDraft, run }) {
  const items = data?.items || []
  const orders = data?.orders || []
  const ledgers = data?.ledgers || []
  const empty = { title:'', description:'', price:0, stock:-1, category:'GIFT_GENERAL', cover_icon:'fa-gift', enabled:true, payload_json:'{}' }
  const categoryOptions = [
    ['GIFT_GENERAL', '🎁 礼物/通用商品 · 自动发卡密'],
    ['COUPON_TICKET', '🎫 优惠券/兑换券 · 自动发卡密'],
    ['GAME_ITEM', '🎮 游戏道具 · 自动发卡密'],
    ['MEMBER_BENEFIT', '👑 会员/身份权益 · 即时生效'],
    ['THEME_DRESSUP', '🎨 主题/装扮 · 即时生效'],
    ['RARE_PERK', '💎 稀有权益 · 即时生效'],
    ['COFFEE_SPONSOR', '☕ 咖啡/赞助 · 人工处理'],
    ['PERIPHERAL_PHYSICAL', '👕 周边/实物 · 人工发货'],
  ]
  const categoryIcons = { GIFT_GENERAL:'fa-gift', COUPON_TICKET:'fa-ticket', GAME_ITEM:'fa-gamepad', MEMBER_BENEFIT:'fa-crown', THEME_DRESSUP:'fa-palette', RARE_PERK:'fa-gem', COFFEE_SPONSOR:'fa-mug-hot', PERIPHERAL_PHYSICAL:'fa-shirt' }
  const systemProducts = {
    MEMBER_BENEFIT: [
      { title:'改名卡', description:'兑换后提交想修改的新昵称，管理员审核后处理。', cover_icon:'fa-id-card', payload_json:'{"request_type":"rename"}' },
      { title:'头衔申请券', description:'提交你想展示的个人头衔，管理员审核后处理。', cover_icon:'fa-crown', payload_json:'{"request_type":"custom_title"}' },
      { title:'VIP会员30天', description:'系统自动开通 VIP 身份 30 天。', cover_icon:'fa-crown', payload_json:'{"vip_days":30}' },
      { title:'VIP会员90天', description:'系统自动开通 VIP 身份 90 天。', cover_icon:'fa-crown', payload_json:'{"vip_days":90}' },
    ],
    THEME_DRESSUP: [
      { title:'深色主题', description:'系统自动解锁深色主题。', cover_icon:'fa-palette', payload_json:'{"theme_id":"dark"}' },
      { title:'主页背景·清晨蓝', description:'个人主页资料卡切换为清晨蓝浅渐变背景，清爽克制。', cover_icon:'fa-image', payload_json:'{"effect":"profile_theme","key":"morning_blue"}' },
      { title:'主页背景·桃雾粉', description:'个人主页资料卡切换为低饱和桃粉渐变，柔和不刺眼。', cover_icon:'fa-image', payload_json:'{"effect":"profile_theme","key":"peach_blush"}' },
      { title:'主页背景·薄荷玻璃', description:'个人主页资料卡切换为薄荷绿玻璃感浅色背景。', cover_icon:'fa-image', payload_json:'{"effect":"profile_theme","key":"mint_glass"}' },
      { title:'主页背景·薰衣草雾', description:'个人主页资料卡切换为淡紫雾面背景，适合低调装饰。', cover_icon:'fa-image', payload_json:'{"effect":"profile_theme","key":"lavender_mist"}' },
      { title:'主页背景·日落金', description:'个人主页资料卡切换为浅金日落渐变，温暖但不夸张。', cover_icon:'fa-image', payload_json:'{"effect":"profile_theme","key":"sunset_gold"}' },
      { title:'头像颜色卡·绿色', description:'绿色头像外环，清爽初级身份标识。', cover_icon:'fa-circle', payload_json:'{"effect":"avatar_border_style","key":"avatar_border_green","style":"#34D399","tier":"初级"}' },
      { title:'头像颜色卡·蓝色', description:'蓝色头像外环，标准活跃成员标识。', cover_icon:'fa-circle', payload_json:'{"effect":"avatar_border_style","key":"avatar_border_blue","style":"#60A5FA","tier":"标准"}' },
      { title:'头像颜色卡·紫色', description:'紫色头像外环，高级个性身份标识。', cover_icon:'fa-circle', payload_json:'{"effect":"avatar_border_style","key":"avatar_border_purple","style":"#A78BFA","tier":"高级"}' },
      { title:'头像颜色卡·粉色', description:'粉色头像外环，幻彩醒目身份标识。', cover_icon:'fa-circle', payload_json:'{"effect":"avatar_border_style","key":"avatar_border_pink","style":"#F472B6","tier":"幻彩"}' },
      { title:'头像颜色卡·金色', description:'金色头像外环，至尊成员身份标识。', cover_icon:'fa-crown', payload_json:'{"effect":"avatar_border_style","key":"avatar_border_gold","style":"#FBBF24","tier":"至尊"}' },
      { title:'谷歌至尊四色环', description:'谷歌官方四色渐变头像环，神话级尊贵标识。', cover_icon:'fa-gem', payload_json:'{"effect":"avatar_border_style","key":"avatar_border_google","style":"conic-gradient(#4285F4, #EA4335, #FBBC05, #34A853, #4285F4)","tier":"神话级"}' },
    ],
    RARE_PERK: [
      { title:'红色用户名', description:'稀有权益：用户名显示为红色，覆盖个人信息面板、帖子列表和评论区。', cover_icon:'fa-gem', payload_json:'{"perk":"red_username"}' },
    ],
  }
  const item = draft.marketItem || empty
  const editing = Boolean(item.id)
  const cardCats = new Set(['GIFT_GENERAL','COUPON_TICKET','GAME_ITEM'])
  const directCats = new Set(['MEMBER_BENEFIT','THEME_DRESSUP','RARE_PERK'])
  const currentSystemProducts = systemProducts[item.category] || []
  const selectedSystemProduct = currentSystemProducts.find(p => p.title === item.title) || currentSystemProducts[0]
  const normalizeItem = src => directCats.has(src.category) && selectedSystemProduct
    ? { ...src, title: selectedSystemProduct.title, description: selectedSystemProduct.description, cover_icon: selectedSystemProduct.cover_icon || categoryIcons[src.category] || 'fa-gift', payload_json: selectedSystemProduct.payload_json || '{}' }
    : { ...src, cover_icon: src.cover_icon || categoryIcons[src.category] || 'fa-gift', payload_json: src.payload_json || '{}' }
  const save = () => {
    const payload = normalizeItem({ ...item, price:Number(item.price || 0), stock:Number(item.stock ?? -1), enabled:item.enabled !== false })
    return run(() => api(editing ? `/api/admin/market/items/${item.id}` : '/api/admin/market/products', { method: editing ? 'PUT' : 'POST', body: JSON.stringify(payload) }).then(() => setDraft({ ...draft, marketItem: empty })))
  }
  const edit = x => setDraft({ ...draft, marketItem: { ...x, enabled: Boolean(x.enabled), payload_json:x.payload_json || '{}' } })
  const setCategory = category => {
    const products = systemProducts[category] || []
    const first = products[0]
    setDraft({ ...draft, marketItem: { ...item, category, cover_icon: categoryIcons[category] || 'fa-gift', ...(first ? first : { title:'', description:item.description || '', payload_json:'{}' }) } })
  }
  const setSystemProduct = title => {
    const picked = currentSystemProducts.find(p => p.title === title) || currentSystemProducts[0]
    if (picked) setDraft({ ...draft, marketItem: { ...item, ...picked } })
  }
  const addKeys = x => {
    const keys = prompt(`给「${x.title}」导入卡密，一行一个：`, '')
    if (!keys?.trim()) return
    run(() => api('/api/admin/market/add-keys', { method:'POST', body: JSON.stringify({ product_id:x.id, keys_text:keys }) }))
  }
  const setEnabled = (x, enabled) => run(() => api(`/api/admin/market/items/${x.id}/enabled`, { method:'PATCH', body: JSON.stringify({ enabled }) }))
  const applyOrderPatch = order => {
    if (!order) return
    setAdminData(prev => ({
      ...prev,
      market: {
        ...(prev.market || {}),
        orders: (prev.market?.orders || []).map(x => x.id === order.id ? { ...x, ...order } : x)
      }
    }))
  }
  const fulfill = o => {
    const text = prompt(`处理订单 #${o.id}，填写快递单号或处理结果：`, o.delivered_content || '')
    if (!text?.trim()) return
    run(() => api(`/api/admin/market/orders/${o.id}/fulfill`, { method:'PUT', body: JSON.stringify({ delivered_content:text.trim() }) }), { reload:false, apply: r => applyOrderPatch(r?.order) }).catch(()=>{})
  }
  const audit = (o, approved) => {
    const reject_reason = approved ? '' : prompt(`拒绝订单 #${o.id} 的原因：`, '申请内容不符合社区规范')
    if (!approved && !reject_reason?.trim()) return
    run(() => api(`/api/admin/market/audit/${o.id}`, { method:'PUT', body: JSON.stringify({ approved, reject_reason: reject_reason || '' }) }), { reload:false, apply: r => applyOrderPatch(r?.order) }).catch(()=>{})
  }
  const adminOrderMeta = o => `${o.cost_points || o.price} 泓币 · ${orderStatusText(o.status)} · ${displayTime(o.created_at)}`
  return <div className="admin-card"><h3>泓市场后台</h3>
    <div className="admin-create market-admin-create">
      {directCats.has(item.category) ? <select className="form-input" value={selectedSystemProduct?.title || item.title || ''} onChange={e => setSystemProduct(e.target.value)}>{currentSystemProducts.map(p => <option key={p.title} value={p.title}>{p.title}</option>)}</select> : <input className="form-input" placeholder="商品名" value={item.title || ''} onChange={e => setDraft({ ...draft, marketItem: { ...item, title:e.target.value, cover_icon: categoryIcons[item.category] || item.cover_icon || 'fa-gift' } })} />}
      <input className="form-input" type="number" min="0" placeholder="价格" value={item.price ?? 0} onChange={e => setDraft({ ...draft, marketItem: { ...item, price:e.target.value } })} />
      <input className="form-input" type="number" min="-1" placeholder="库存，-1为不限" value={item.stock ?? -1} onChange={e => setDraft({ ...draft, marketItem: { ...item, stock:e.target.value } })} />
      <select className="form-input" value={item.category || 'GIFT_GENERAL'} onChange={e => setCategory(e.target.value)}>{categoryOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
      <textarea className="form-textarea channel-desc" placeholder="商品说明" value={directCats.has(item.category) ? (selectedSystemProduct?.description || item.description || '') : (item.description || '')} readOnly={directCats.has(item.category)} onChange={e => setDraft({ ...draft, marketItem: { ...item, description:e.target.value } })} />
      <label className="channel-enabled"><input type="checkbox" checked={item.enabled !== false} onChange={e => setDraft({ ...draft, marketItem: { ...item, enabled:e.target.checked } })} /> 上架</label>
      <div className="admin-actions"><button className="btn btn-primary" disabled={!item.title?.trim()} onClick={save}>{editing ? '保存商品' : '创建商品'}</button>{editing && <button className="btn btn-secondary" onClick={() => setDraft({ ...draft, marketItem: empty })}>取消编辑</button>}</div>
    </div>
    <h3>商品列表</h3>
    {items.map(x => <div className="admin-row" key={x.id}><div><b><i className={`fas ${x.cover_icon || 'fa-gift'}`} /> {x.title}</b><p>{x.price} 泓币 · {x.stock < 0 ? '不限库存' : `库存 ${x.stock}`} · {x.enabled ? '上架中' : '已下架'} · {x.fulfillment_method}</p><small>{x.description}{cardCats.has(x.category) ? ` · 可用卡密 ${x.card_key_available || 0}` : ''}{x.orders_count ? ` · 兑换记录 ${x.orders_count} 条` : ''}</small></div><div className="admin-actions"><button className="btn btn-sm btn-secondary" onClick={() => edit(x)}>编辑</button>{cardCats.has(x.category) && <button className="btn btn-sm btn-secondary" onClick={() => addKeys(x)}>导入卡密</button>}{x.enabled ? <button className="btn btn-sm btn-secondary" onClick={() => setEnabled(x, false)}>下架</button> : <button className="btn btn-sm btn-primary" onClick={() => setEnabled(x, true)}>重新上架</button>}<button className="btn btn-sm btn-danger" onClick={() => confirm(x.orders_count ? '这个商品已有兑换记录，将下架并保留历史记录。确定继续？' : '确定永久删除这个商品？') && run(() => api(`/api/admin/market/items/${x.id}`, { method:'DELETE' }))}>{x.orders_count ? '删除/下架' : '永久删除'}</button></div></div>)}
    <h3>最近兑换</h3>
    {orders.length ? orders.map(o => <div className="admin-row" key={o.id}><div><b>{o.username} 兑换 {o.item_title}</b><p>{adminOrderMeta(o)}</p><small>{o.payload ? `申请：${decodeOrderNote(o.payload)}` : o.shipping_info ? `收货/备注：${decodeOrderNote(o.shipping_info)}` : ''} {o.delivered_content ? `结果：${decodeOrderNote(o.delivered_content)}` : ''}</small></div><div className="admin-actions">{o.status === 'PENDING_AUDIT' && <><button className="btn btn-sm btn-success" onClick={() => audit(o, true)}>通过</button><button className="btn btn-sm btn-danger" onClick={() => audit(o, false)}>拒绝并退款</button></>}{o.status === 'PENDING' && <button className="btn btn-sm btn-primary" onClick={() => fulfill(o)}>处理/发货</button>}</div></div>) : <div className="empty-state"><i className="fas fa-receipt" /><p>暂无兑换记录</p></div>}
    <h3>积分流水</h3>
    {ledgers.length ? ledgers.map(l => <div className="admin-line" key={l.id}><span>{l.username} · {l.reason}</span><span className={l.delta >= 0 ? 'ledger-plus' : 'ledger-minus'}>{l.delta > 0 ? '+' : ''}{l.delta}</span></div>) : <div className="empty-state"><i className="fas fa-coins" /><p>暂无流水</p></div>}
  </div>
}


function AdminSettings({ data, draft, setDraft, run }) {
  const s = draft.settings || data?.settings || {}
  const set = (k, v) => setDraft({ ...draft, settings: { ...s, [k]: v } })
  const save = () => run(() => api('/api/admin/settings', { method:'PUT', body: JSON.stringify(s) }).then(r => { chromeCache = null; chromePromise = null; window.dispatchEvent(new CustomEvent('app:settings-updated', { detail:r.settings })); return r }), { reload:false })
  return <div className="admin-card"><h3><i className="fas fa-gear" /> 系统设置</h3>
    <div className="settings-grid">
      <label><span>网站名字</span><input className="form-input" value={s.site_name || ''} placeholder="泓聊社区" onChange={e => set('site_name', e.target.value)} /></label>
      <label><span>网站 Logo URL</span><input className="form-input" value={s.site_logo || ''} placeholder="/uploads/logo.png 或 https://..." onChange={e => set('site_logo', e.target.value)} /></label>
      <label><span>默认用户头像</span><input className="form-input" value={s.default_avatar || ''} placeholder="新用户默认头像 URL" onChange={e => set('default_avatar', e.target.value)} /></label>
      <label><span>登录/注册验证码</span><select className="form-select" value={s.captcha_enabled ? '1' : '0'} onChange={e => set('captcha_enabled', e.target.value === '1')}><option value="0">关闭：登录注册不显示验证码（默认）</option><option value="1">开启：登录注册必须填写验证码</option></select></label>
      <label><span>限制访客浏览</span><select className="form-select" value={s.guest_access_restricted ? '1' : '0'} onChange={e => set('guest_access_restricted', e.target.value === '1')}><option value="0">关闭：访客可搜索/浏览更多帖子和频道</option><option value="1">开启：搜索、翻页、频道、市场需登录</option></select></label>
      <label><span>邮件通知</span><select className="form-select" value={s.email_enabled ? '1' : '0'} onChange={e => set('email_enabled', e.target.value === '1')}><option value="0">关闭</option><option value="1">开启</option></select></label>
      <label><span>SMTP Host</span><input className="form-input" value={s.smtp_host || ''} onChange={e => set('smtp_host', e.target.value)} /></label>
      <label><span>SMTP Port</span><input className="form-input" type="number" value={s.smtp_port || 465} onChange={e => set('smtp_port', Number(e.target.value || 465))} /></label>
      <label><span>SMTP 用户</span><input className="form-input" value={s.smtp_user || ''} onChange={e => set('smtp_user', e.target.value)} /></label>
      <label><span>SMTP 密码</span><input className="form-input" type="password" value={s.smtp_password || ''} placeholder="留空或 *** 表示不修改" onChange={e => set('smtp_password', e.target.value)} /></label>
      <label><span>发件人</span><input className="form-input" value={s.smtp_from || ''} onChange={e => set('smtp_from', e.target.value)} /></label>
      <label><span>同一帖子24小时邮件上限</span><input className="form-input" type="number" min="0" max="100" value={s.comment_email_limit_24h ?? 8} onChange={e => set('comment_email_limit_24h', Number(e.target.value || 0))} /></label>
      <label><span>栖岛第三方登录</span><select className="form-select" value={s.qidao_oauth_enabled ? '1' : '0'} onChange={e => set('qidao_oauth_enabled', e.target.value === '1')}><option value="0">关闭</option><option value="1">开启：登录页显示栖岛账号登录</option></select></label>
      <label><span>栖岛 Client ID</span><input className="form-input" value={s.qidao_client_id || ''} placeholder="应用ID" onChange={e => set('qidao_client_id', e.target.value)} /></label>
      <label><span>栖岛 Client Secret</span><input className="form-input" type="password" value={s.qidao_client_secret || ''} placeholder="留空或 *** 表示不修改" onChange={e => set('qidao_client_secret', e.target.value)} /></label>
      <label><span>栖岛 Scope</span><input className="form-input" value={s.qidao_scope || 'profile email'} placeholder="profile email" onChange={e => set('qidao_scope', e.target.value)} /></label>
      <label className="settings-wide"><span>首页跑马灯 JSON</span><textarea className="form-textarea" value={s.banners_json || ''} placeholder='[{"tag":"HOT","content":"欢迎加入泓聊社区","color":"cyan"}]' onChange={e => set('banners_json', e.target.value)} /></label>
    </div>
    <div className="alert alert-info">访客限制默认关闭：未登录用户可以搜索、翻页浏览帖子、频道和泓市场；发帖、评论、签到、兑换、后台仍需登录。</div>
    <div className="alert alert-info">栖岛回调地址请在开放平台配置为：<code>{location.origin}/api/oauth/qidao/callback</code>。Client Secret 仅后端保存，前台不会下发。</div>
    <div className="alert alert-info">跑马灯支持 tag/content/color；被评论会生成红色站内气泡，点击单条后红点消失，也可全部已读。</div>
    <div className="admin-actions settings-actions"><button className="btn btn-primary" onClick={save}>保存系统设置</button></div>
  </div>
}


function ExchangeModal({ item, balance, busy, onClose, onSubmit }) {
  const [step, setStep] = useState('confirm')
  const [value, setValue] = useState('')
  const [localErr, setLocalErr] = useState('')
  useEffect(() => {
    setStep('confirm')
    setValue('')
    setLocalErr('')
  }, [item?.id])
  if (!item) return null
  const type = item.title === '改名卡' ? 'rename' : (item.title === '头衔申请券' || item.title === '自定义头衔卡') ? 'title' : ''
  const isAudit = Boolean(type)
  const isInstantDressup = isInstantDressupItem(item)
  const isBorder = isAvatarBorderItem(item)
  const label = type === 'rename' ? '新用户名' : '期望头衔名称'
  const hint = type === 'rename' ? '必须以字母开头，只能包含字母、数字和下划线。' : '建议 2-12 个字，管理员审核后展示在个人资料和帖子旁。'
  const usernameOk = /^[a-zA-Z][a-zA-Z0-9_]*$/.test(value.trim())
  const canSubmit = !busy && value.trim() && (type !== 'rename' || usernameOk)
  const submit = async () => {
    const v = value.trim()
    if (type === 'rename' && !usernameOk) return setLocalErr('用户名必须以字母开头，且只能包含字母、数字和下划线！')
    if (!v) return setLocalErr(`请填写${label}`)
    setLocalErr('')
    await onSubmit(item, v)
    setStep('done')
  }
  return <div className="exchange-mask" role="dialog" aria-modal="true"><div className={`exchange-modal exchange-step-${step}`}>
    <button className="exchange-close" onClick={onClose} disabled={busy} aria-label="关闭"><i className="fas fa-xmark" /></button>
    <div className="exchange-icon"><i className={`fas ${step === 'done' ? 'fa-check' : item.cover_icon || 'fa-gift'}`} /></div>
    {step === 'confirm' && <><h3>确认兑换「{item.title}」？</h3><p>将扣除 <b>{item.price}</b> 泓币，当前余额 {Number(balance || 0).toLocaleString()} 泓币。{isBorder && <><br />兑换后装扮将立即生效。</>}</p><div className="exchange-actions"><button className="btn btn-secondary" onClick={onClose}>取消</button><button className="btn btn-primary" onClick={async () => { if (isAudit) return setStep('form'); await onSubmit(item); if (isInstantDressup) setStep('done') }} disabled={busy || (balance || 0) < item.price}>{busy ? '提交中...' : '确认兑换'}</button></div></>}
    {step === 'form' && <><h3>{item.title}申请信息</h3><p>确认后会先扣除泓币，订单进入待审核；拒绝时系统自动退款。</p><label className="exchange-field"><span>{label}</span><input autoFocus className={`form-input ${localErr ? 'input-error' : ''}`} value={value} maxLength={32} onChange={e => { setValue(e.target.value); setLocalErr('') }} placeholder={type === 'rename' ? 'New_Name123' : '例如：社区共创者'} /></label><small className={type === 'rename' && value && !usernameOk ? 'field-error' : 'field-hint'}>{type === 'rename' && value && !usernameOk ? '用户名必须以字母开头，且只能包含字母、数字和下划线！' : hint}</small>{localErr && <div className="alert alert-error compact-alert">{localErr}</div>}<div className="exchange-actions"><button className="btn btn-secondary" onClick={() => setStep('confirm')} disabled={busy}>返回</button><button className="btn btn-primary" onClick={submit} disabled={!canSubmit}>{busy ? '提交中...' : '提交审核'}</button></div></>}
    {step === 'done' && <><h3>{isInstantDressup ? '装扮已生效' : '申请已提交'}</h3><p>{isInstantDressup ? '新的社区装扮已秒级生效，去个人主页、帖子和评论里看看效果吧。' : '申请已提交，请等待管理员审核。'}</p><div className="exchange-actions"><button className="btn btn-primary" onClick={onClose}>知道了</button></div></>}
  </div></div>
}

function MarketPage({ me, setMe }) {
  const [data, setData] = useState(null)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(0)
  const [showOrders, setShowOrders] = useState(true)
  const [activeItem, setActiveItem] = useState(null)
  const load = () => api('/api/market').then(d => { setData(d); document.title = '泓市场 - 泓聊社区' }).catch(e => setErr(e.message))
  useEffect(() => { document.title = '泓市场 - 泓聊社区'; setData(null); setErr(''); load() }, [])
  async function buy(item, auditValue = '') {
    const isAuditItem = item.title === '改名卡' || item.title === '头衔申请券' || item.title === '自定义头衔卡'
    const isInstantItem = isInstantDressupItem(item)
    const body = { item_id: item.id }
    if (!isAuditItem && !isInstantItem && item.category === 'PERIPHERAL_PHYSICAL') {
      const shipping_name = prompt('收货人姓名：', '')
      if (!shipping_name?.trim()) return
      const shipping_phone = prompt('联系电话：', '')
      if (!shipping_phone?.trim()) return
      const shipping_address = prompt('收货地址：', '')
      if (!shipping_address?.trim()) return
      Object.assign(body, { shipping_name:shipping_name.trim(), shipping_phone:shipping_phone.trim(), shipping_address:shipping_address.trim() })
    }
    setBusy(item.id); setErr('')
    try {
      const endpoint = isAuditItem ? '/api/market/exchange' : '/api/market/buy'
      const r = await api(endpoint, { method:'POST', body: JSON.stringify(isAuditItem ? { item_id:item.id, value:auditValue } : body) })
      notify(isAuditItem ? '申请已提交，请等待管理员审核' : (isInstantItem ? '装扮已生效' : (r.status === 'PENDING' ? '兑换成功，等待管理员处理' : '兑换成功')), 'success')
      if (r.user) { syncStoredUser(r.user); setMe?.(r.user) }
      else if (r.current_points !== undefined) { const u = mergeStoredUser({ available_points: r.current_points }); if (u?.id) setMe?.(u) }
      setData(d => ({
        ...d,
        balance: r.current_points ?? r.balance ?? d?.balance ?? 0,
        orders: r.order ? [r.order, ...(d?.orders || []).filter(o => o.id !== r.order.id)].slice(0, 8) : (d?.orders || []),
        items: (d?.items || []).map(x => x.id === item.id && x.stock > 0 ? { ...x, stock: x.stock - 1 } : x)
      }))
      return r
    } catch (e) {
      setErr(e.message); notify(e.message, 'error'); throw e
    } finally { setBusy(0) }
  }
  async function checkin() {
    setErr('')
    try { const r = await api('/api/points/checkin', { method:'POST' }); notify(r.already ? `今天已签到，连续 ${r.streak} 天` : `签到成功 +${r.earned} 泓币，连续 ${r.streak} 天`, 'success'); setData(d => ({ ...d, balance:r.balance })) }
    catch (e) { setErr(e.message); notify(e.message, 'error') }
  }
  if (!data && !err) return <HomeSkeleton />
  const pendingAuditItemIds = new Set((data?.orders || []).filter(o => o.status === 'PENDING_AUDIT').map(o => o.item_id).filter(Boolean))
  const auditTitles = new Set((data?.orders || []).filter(o => o.status === 'PENDING_AUDIT').map(o => o.title || o.item_title).filter(Boolean))
  const buttonText = item => !me ? '登录后兑换' : (auditTitles.has(item.title) || pendingAuditItemIds.has(item.id) ? '审核中' : ((data.balance || 0) < item.price ? '泓币不足' : item.stock === 0 ? '已售罄' : '兑换'))
  const disabledItem = item => busy === item.id || !me || item.stock === 0 || (data.balance || 0) < item.price || auditTitles.has(item.title) || pendingAuditItemIds.has(item.id)
  return <><PageChrome /><div className="main-content"><div className="market-hero card animate-fadeInUp"><div className="card-body"><span className="channel-pill">泓市场</span><h1>{Number(data?.balance || 0).toLocaleString()} <small>泓币</small></h1><p>{me ? '发帖和评论获得泓币，可兑换社区权益。' : '登录后可签到、兑换和查看个人兑换记录；访客可先浏览商品。'}</p>{me ? <button className="btn btn-secondary" onClick={checkin}><i className="fas fa-calendar-check" /> 每日签到</button> : <a className="btn btn-secondary" href="/login"><i className="fas fa-right-to-bracket" /> 登录后兑换</a>}<div className="market-rules">{(data?.rules || []).map(x => <span key={x}>{x}</span>)}</div></div></div>{err && <div className="alert alert-error">{err}</div>}<div className="market-grid">{data?.items?.map(item => <div className="market-card card animate-fadeInUp" key={item.id}><div className="market-icon"><i className={`fas ${item.cover_icon || 'fa-gift'}`} /></div><div className="market-card-body"><h3>{item.title}</h3><p>{item.description}</p><div className="market-meta"><b>{item.price} 泓币</b><span>{item.stock < 0 ? '不限量' : `库存 ${item.stock}`}</span></div><button className="btn btn-primary market-exchange-btn" disabled={disabledItem(item)} onClick={() => setActiveItem(item)}><i className={`fas ${busy === item.id ? 'fa-spinner fa-spin' : auditTitles.has(item.title) || pendingAuditItemIds.has(item.id) ? 'fa-hourglass-half' : 'fa-bag-shopping'}`} /> {buttonText(item)}</button></div></div>)}</div><div className="card animate-fadeInUp"><div className="card-header fold-head"><h3><i className="fas fa-receipt" /> {me ? '我的兑换记录' : '兑换记录'}</h3><button className="btn btn-sm btn-secondary" onClick={() => setShowOrders(!showOrders)}>{showOrders ? '折叠' : '展开'}</button></div>{showOrders && <div>{data?.orders?.length ? data.orders.map(o => <OrderRow order={o} key={o.id} />) : <div className="empty-state"><i className="fas fa-receipt" /><p>{me ? '暂无兑换记录' : '登录后查看个人兑换记录'}</p></div>}</div>}</div></div><ExchangeModal key={activeItem?.id || 'closed'} item={activeItem} balance={data?.balance || 0} busy={Boolean(busy)} onClose={() => setActiveItem(null)} onSubmit={async (item, value) => { await buy(item, value); if (!(item.title === '改名卡' || item.title === '头衔申请券' || item.title === '自定义头衔卡' || isInstantDressupItem(item))) setActiveItem(null) }} /></>
}

function ChannelsPage() {
  const [data, setData] = useState(null)
  const [err, setErr] = useState('')
  useEffect(() => {
    document.title = '频道 - 泓聊社区'
    let alive = true
    const loadChannels = () => api('/api/channels').then(d => alive && setData(d)).catch(e => { if (alive) { setErr(e.message); if (e.message === '请先登录') clearInterval(timer) } })
    loadChannels()
    const timer = setInterval(() => { if (!document.hidden && !err) loadChannels() }, 15000)
    return () => { alive = false; clearInterval(timer) }
  }, [])
  if (!data && !err) return <HomeSkeleton />
  return <><PageChrome /><div className="main-content"><div className="card animate-fadeInUp"><div className="card-header"><h3><i className="fas fa-broadcast-tower" style={{ color: 'var(--primary)' }} /> 频道</h3></div>{err && <div className="card-body"><div className="alert alert-error">{err}</div></div>}<div className="channel-grid">{data?.items?.length ? data.items.map(ch => <a className="channel-card" href={`/channels/${ch.slug}`} key={ch.id}><div className="channel-icon"><i className="fas fa-broadcast-tower" /></div><div><h3>{ch.name}</h3><p>{ch.description || '管理员频道'}</p><span>{ch.post_count || 0} 条内容 · {ch.mode === 'api' ? '接口对接' : '手动发布'}</span></div></a>) : <div className="empty-state"><i className="fas fa-satellite-dish" /><p>暂无频道</p></div>}</div></div></div></>
}

function ChannelDetail({ slug }) {
  const [data, setData] = useState(null)
  const [err, setErr] = useState('')
  useEffect(() => {
    let alive = true
    setData(null); setErr('')
    const loadChannelPosts = (silent = false) => api(`/api/channels/${slug}/posts`).then(d => { if (alive) { setData(d); document.title = `${d.channel.name} - 频道` } }).catch(e => { if (alive && !silent) setErr(e.message) })
    loadChannelPosts(false)
    const timer = setInterval(() => { if (!document.hidden) loadChannelPosts(true) }, 10000)
    return () => { alive = false; clearInterval(timer) }
  }, [slug])
  if (!data && !err) return <HomeSkeleton />
  if (err) return <><PageChrome /><div className="main-content"><div className="alert alert-error">{err}</div></div></>
  return <><PageChrome /><div className="main-content"><div className="detail-wrap">
    <div className="channel-hero card"><div className="card-body"><span className="channel-pill">频道</span><h1>{data.channel.name}</h1><p>{data.channel.description || '频道内容由管理员发布，用户可浏览和评论。'}</p></div></div>
    <div className="card"><div className="card-header"><h3><i className="fas fa-list" /> 最新内容</h3></div>
      {data.items.length ? data.items.map((p, idx) => <div className="post-item channel-post-row" key={p.id}>
        <a className="channel-post-main" href={`/channel-post/${p.id}`}><div className="post-title">{p.title}</div><div className="post-preview">{htmlText(p.preview)}</div></a>
        <div className="post-meta"><span><i className="fas fa-user-shield" /> {p.author_name || '管理员'}</span><span><i className="far fa-clock" /> {relativeTime(p.time)}</span><span><i className="far fa-comment" /> {p.comments || 0}</span><span><i className="far fa-eye" /> {p.views || 0}</span>{p.external_url && <a className="source-link inline-source" href={p.external_url} target="_blank" rel="noreferrer"><i className="fas fa-arrow-up-right-from-square" /> {sourceLinkLabel(p.external_url)}</a>}</div>
      </div>) : <div className="empty-state"><i className="fas fa-inbox" /><p>这个频道暂时没有内容</p></div>}
    </div>
    <div className="back-home"><a className="btn btn-secondary" href="/channels"><i className="fas fa-arrow-left" /> 返回频道</a></div>
  </div></div></>
}

function ChannelPostDetail({ id, me }) {
  const [data, setData] = useState(null)
  const [content, setContent] = useState('')
  const [err, setErr] = useState('')
  const [sending, setSending] = useState(false)
  const load = () => api(`/api/channel_posts/${id}`).then(d => { setData(d); document.title = `${d.post.title} - 频道` }).catch(e => setErr(e.message))
  useEffect(() => { let alive = true; setData(null); setErr(''); api(`/api/channel_posts/${id}`).then(d => { if (alive) { setData(d); document.title = `${d.post.title} - 频道` } }).catch(e => alive && setErr(e.message)); return () => { alive = false } }, [id])
  async function comment(e) { e.preventDefault(); setErr(''); if (!content.trim()) return setErr('评论内容不能为空')
    if (content.trim().length < 16) return setErr('评论至少需要 16 个字'); setSending(true); try { const r = await api(`/api/channel_posts/${id}/comments`, { method: 'POST', body: JSON.stringify({ content: content.trim() }) }); if (r.comment) setData(d => d ? { ...d, comments: [...(d.comments || []), r.comment], post: { ...d.post, comments: Number(d.post.comments || 0) + 1 } } : d); setContent(''); notify('评论已发表', 'success') } catch (e) { setErr(e.message); notify(e.message, 'error') } finally { setSending(false) } }
  if (err && !data) return <><PageChrome /><div className="main-content"><div className="alert alert-error">{err}</div></div></>
  if (!data) return <DetailSkeleton />
  const p = data.post
  return <><PageChrome /><div className="main-content"><div className="detail-wrap">
    <div className="card animate-fadeInUp post-detail-card"><div className="card-header post-detail-header"><span className="channel-pill">{p.channel_name}</span><h2>{p.title}</h2><div className="post-meta detail-meta"><div className="post-meta-item"><i className="fas fa-user-shield" /> {p.author_name || '管理员'}</div><div className="post-meta-item"><i className="far fa-clock" /> {relativeTime(p.time)}</div><div className="post-meta-item detail-counts"><i className="far fa-comment" /> {data.comments.length || 0}<span className="meta-split">|</span><i className="far fa-eye" /> {p.views || 0}</div></div></div><div className="card-body"><div className="markdown-body">{renderContent(p.content)}</div>{p.external_url && <a className="source-link" href={p.external_url} target="_blank" rel="noreferrer"><i className="fas fa-arrow-up-right-from-square" /> {sourceLinkLabel(p.external_url)}</a>}</div></div>
    <div className="card animate-fadeInUp reply-card"><div className="card-header"><h3><i className="fas fa-comments" /> 评论 ({data.comments.length})</h3></div><div>{data.comments.length ? data.comments.map(c => <div className={`post-item reply-item ${commentThemeClass(c)}`} key={c.id}><div className="reply-row"><AvatarRing user={c} src={c.avatar} size={48} className="post-avatar-ring" /><div className="reply-main"><div className="reply-head"><a className={`post-author-name ${usernameClass(c)}`} href={`/user/${c.user_id || ''}`}>{c.author}</a><UsernameBadge user={c} /><span><i className="far fa-clock" /> {relativeTime(c.time)}</span></div><div className="markdown-body reply-content"><p>{c.content}</p></div></div></div></div>) : <div className="empty-state"><i className="fas fa-comment-dots" /><p>暂无评论</p></div>}</div></div>
    <div className="card"><div className="card-body reply-form-body">{err && <div className="alert alert-error">{err}</div>}{me ? <form onSubmit={comment}><textarea className="form-textarea" required maxLength={2000} value={content} onChange={e => setContent(e.target.value)} placeholder="写下你的评论" /><button className="btn btn-primary" style={{ marginTop: 10 }} disabled={sending}><i className={`fas ${sending ? 'fa-spinner fa-spin' : 'fa-paper-plane'}`} /> {sending ? '发送中' : '发表评论'}</button></form> : <><p>登录后即可评论</p><a className="btn btn-primary" href="/login"><i className="fas fa-right-to-bracket" /> 去登录</a></>}</div></div>
    <div className="back-home"><a className="btn btn-secondary" href={`/channels/${p.channel_slug}`}><i className="fas fa-arrow-left" /> 返回频道</a></div>
  </div></div></>
}

function AdminChannels({ data, draft, setDraft, run }) {
  const channels = data?.items || []
  const posts = data?.posts || []
  const emptyChannel = { name:'', slug:'', description:'', mode:'manual', enabled:true, source_type:'telegram', endpoint_url:'', auth_type:'bearer', auth_secret_ref:'TG_MONITOR_API_KEY', mapping_json:'{}' }
  const ch = draft.channel || emptyChannel
  const editing = Boolean(ch.id)
  const post = draft.channelPost || { channel_id: channels[0]?.id || '', title:'', content:'', author_name:'管理员', external_url:'' }
  const editChannel = (c) => setDraft({ ...draft, channel: { ...c, auth_secret_ref: c.auth_secret_ref && c.auth_secret_ref !== '***' ? c.auth_secret_ref : (c.mode === 'api' ? 'TG_MONITOR_API_KEY' : '') } })
  const resetChannel = () => setDraft({ ...draft, channel: emptyChannel })
  const saveChannel = () => run(() => api(editing ? `/api/admin/channels/${ch.id}` : '/api/admin/channels', { method: editing ? 'PUT' : 'POST', body: JSON.stringify(ch) }).then(() => setDraft({ ...draft, channel: emptyChannel })))
  const publish = () => run(() => api(`/api/admin/channels/${post.channel_id}/posts`, { method:'POST', body: JSON.stringify(post) }).then(() => setDraft({ ...draft, channelPost: undefined })))
  return <div className="admin-card"><h3>频道管理</h3>
    <div className="admin-create channel-create">
      <input className="form-input" placeholder="频道名，如 linux.do" value={ch.name || ''} onChange={e => setDraft({ ...draft, channel: { ...ch, name: e.target.value, slug: ch.slug || e.target.value.toLowerCase().replace(/\s+/g,'-') } })} />
      <input className="form-input" placeholder="slug，如 linux-do" value={ch.slug || ''} onChange={e => setDraft({ ...draft, channel: { ...ch, slug: e.target.value } })} />
      <select className="form-select" value={ch.mode || 'manual'} onChange={e => setDraft({ ...draft, channel: { ...ch, mode: e.target.value } })}><option value="manual">手动发帖</option><option value="api">接口对接</option></select>
      <label className="channel-enabled"><input type="checkbox" checked={ch.enabled !== false} onChange={e => setDraft({ ...draft, channel: { ...ch, enabled: e.target.checked } })} /> 启用</label>
      <textarea className="form-textarea channel-desc" placeholder="频道说明" value={ch.description || ''} onChange={e => setDraft({ ...draft, channel: { ...ch, description: e.target.value } })} />
      {ch.mode === 'api' && <><input className="form-input channel-full" placeholder="接口地址" value={ch.endpoint_url || ''} onChange={e => setDraft({ ...draft, channel: { ...ch, endpoint_url: e.target.value } })} /><input className="form-input" placeholder="凭据引用名（不填明文密钥）" value={ch.auth_secret_ref || ''} onChange={e => setDraft({ ...draft, channel: { ...ch, auth_secret_ref: e.target.value } })} /></>}
      <div className="admin-actions channel-full"><button className="btn btn-primary" onClick={saveChannel} disabled={!ch.name?.trim() || !ch.slug?.trim()}>{editing ? '保存频道' : '创建频道'}</button>{editing && <button className="btn btn-secondary" onClick={resetChannel}>取消编辑</button>}</div>
    </div>
    <div className="admin-create channel-post-create"><select className="form-select" value={post.channel_id || ''} onChange={e => setDraft({ ...draft, channelPost: { ...post, channel_id: e.target.value } })}>{channels.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select><input className="form-input" placeholder="频道内容标题" value={post.title || ''} onChange={e => setDraft({ ...draft, channelPost: { ...post, title: e.target.value } })} /><input className="form-input" placeholder="作者名，默认管理员" value={post.author_name || ''} onChange={e => setDraft({ ...draft, channelPost: { ...post, author_name: e.target.value } })} /><textarea className="form-textarea channel-desc" placeholder="频道内容正文" value={post.content || ''} onChange={e => setDraft({ ...draft, channelPost: { ...post, content: e.target.value } })} /><button className="btn btn-primary" onClick={publish} disabled={!post.channel_id || !post.title?.trim() || !post.content?.trim()}>发布频道内容</button></div>
    {channels.length ? channels.map(c => <div className="admin-row" key={c.id}><div><b>{c.name}</b><p>{c.slug} · {c.mode === 'api' ? '接口对接' : '手动发布'} · {c.enabled ? '启用' : '停用'} · 内容 {c.post_count || 0}</p><small>{c.description || '无说明'}</small></div><div className="admin-actions"><button className="btn btn-sm btn-secondary" onClick={() => editChannel(c)}>编辑</button><a className="btn btn-sm btn-secondary" href={`/channels/${c.slug}`}>查看</a>{c.mode === 'api' && <button className="btn btn-sm btn-secondary" onClick={() => run(() => api(`/api/admin/channels/${c.id}/test-source`, { method:'POST' }))}>测试接口</button>}{c.mode === 'api' && <button className="btn btn-sm btn-secondary" onClick={() => run(() => api(`/api/admin/channels/${c.id}/sync`, { method:'POST' }))}>立即同步</button>}<button className="btn btn-sm btn-danger" onClick={() => confirm('确定删除频道及内容？') && run(() => api(`/api/admin/channels/${c.id}`, { method:'DELETE' }))}>删除</button></div></div>) : <div className="empty-state"><i className="fas fa-satellite-dish" /><p>暂无频道，先创建一个</p></div>}
    {posts.length > 0 && <><h3>频道内容</h3>{posts.map(p => <div className="admin-row" key={p.id}><div><b>{p.title}</b><p>{p.channel_name} · {p.author_name} · {p.time} · 评论 {p.comments || 0}</p></div><div className="admin-actions"><a className="btn btn-sm btn-secondary" href={`/channel-post/${p.id}`}>查看</a><button className="btn btn-sm btn-danger" onClick={() => confirm('确定删除这条频道内容？') && run(() => api(`/api/admin/channel_posts/${p.id}`, { method:'DELETE' }))}>删除</button></div></div>)}</>}
  </div>
}


function notify(message, type = 'info') {
  window.dispatchEvent(new CustomEvent('app:toast', { detail: { message, type } }))
}

function ToastHost() {
  const [items, setItems] = useState([])
  useEffect(() => {
    const onToast = e => {
      const id = Date.now() + Math.random()
      setItems(v => [...v, { id, ...e.detail }])
      setTimeout(() => setItems(v => v.filter(x => x.id !== id)), 2600)
    }
    window.addEventListener('app:toast', onToast)
    return () => window.removeEventListener('app:toast', onToast)
  }, [])
  return <div className="toast-host">{items.map(t => <div key={t.id} className={`toast toast-${t.type || 'info'}`}><i className={`fas ${t.type === 'success' ? 'fa-check-circle' : t.type === 'error' ? 'fa-triangle-exclamation' : 'fa-circle-info'}`} /> {t.message}</div>)}</div>
}

function PostListSkeleton({ count = 6 }) { return <>{Array.from({ length: count }).map((_, i) => <div className="post-item skeleton-row" key={i}><span className="skeleton-avatar" /><div className="skeleton-main"><span className="skeleton-line w70" /><span className="skeleton-line w95" /><span className="skeleton-line w45" /></div></div>)}</> }
function HomeSkeleton() { return <><PageChrome /><div className="main-content"><div className="skeleton-search skeleton-shimmer" /><div className="home-layout"><div className="card"><div className="card-header"><h3><i className="fas fa-circle-notch fa-spin" /> 正在加载内容</h3></div><PostListSkeleton /></div><div className="card sidebar-card"><div className="card-header"><h3>侧栏</h3></div><div className="card-body"><span className="skeleton-line w95" /><span className="skeleton-line w70" /></div></div></div></div></> }
function DetailSkeleton() { return <><PageChrome /><div className="main-content"><div className="detail-wrap"><div className="card"><div className="card-body"><span className="skeleton-line w70 big" /><span className="skeleton-line w45" /><span className="skeleton-line w95" /><span className="skeleton-line w95" /><span className="skeleton-line w70" /></div></div></div></div></> }

function TopicDotLoader() { return <><PageChrome /><div className="main-content"><div className="topic-transition-loader" aria-label="帖子加载中"><div className="topic-loader-dots"><span /><span /><span /></div></div></div></> }

function Loading() { return <div className="page-loading"><div className="loading-card"><span className="loading-dot" /> 正在加载...</div></div> }

function App() {
  const path = useRoute()
  const [me, setMe] = useState(null)
  const [site, setSite] = useState(defaultSite)
  useEffect(() => { api('/api/me').then(r => { setMe(r.user); if (r.user) syncStoredUser(r.user) }).catch(() => {}) }, [])
  useEffect(() => {
    const onUserUpdated = e => setMe(e.detail || JSON.parse(localStorage.getItem('yhdet_user') || 'null'))
    window.addEventListener('app:user-updated', onUserUpdated)
    return () => window.removeEventListener('app:user-updated', onUserUpdated)
  }, [])
  useEffect(() => {
    const onExpired = e => { setMe(null); notify(e.detail || '登录状态已失效', 'error'); navigate('/login') }
    window.addEventListener('app:session-expired', onExpired)
    return () => window.removeEventListener('app:session-expired', onExpired)
  }, [])
  useEffect(() => { getChrome().then(d => { if (d.settings) setSite({ ...defaultSite, ...d.settings, stats: d.stats, runtime: d.runtime }) }).catch(() => {}) }, [])
  useEffect(() => {
    const onSettings = e => setSite(s => ({ ...s, ...(e.detail || {}) }))
    window.addEventListener('app:settings-updated', onSettings)
    return () => window.removeEventListener('app:settings-updated', onSettings)
  }, [])
  const page = useMemo(() => {
    const pathname = new URL(path, location.origin).pathname
    if (pathname === '/login') return <AuthPage mode="login" setMe={setMe} site={site} />
    if (pathname === '/register') return <AuthPage mode="register" setMe={setMe} site={site} />
    if (pathname === '/new') return <NewPost me={me} />
    if (pathname === '/channels') return <ChannelsPage />
    if (pathname === '/market') return <MarketPage me={me} setMe={setMe} />
    if (pathname.startsWith('/channels/')) return <ChannelDetail slug={pathname.split('/')[2]} />
    if (pathname.startsWith('/channel-post/')) return <ChannelPostDetail id={pathname.split('/')[2]} me={me} />
    if (pathname === '/admin') return <AdminPage me={me} />
    if (pathname.startsWith('/post/')) return <PostDetail id={pathname.split('/')[2]} me={me} />
    if (pathname.startsWith('/user/')) return <UserPage id={pathname.split('/')[2]} me={me} setMe={setMe} />
    if (pathname === '/games') return <SimpleSection type="games" />
    if (pathname === '/music') return <SimpleSection type="music" />
    return <Home />
  }, [path, me, site])
  const isAuth = new URL(path, location.origin).pathname === '/login' || new URL(path, location.origin).pathname === '/register'
  return <>{isAuth ? page : <><Nav me={me} setMe={setMe} path={path} site={site} />{page}<SiteFooter site={site} /></>}<ToastHost /></>
}

createRoot(document.getElementById('root')).render(<App />)





