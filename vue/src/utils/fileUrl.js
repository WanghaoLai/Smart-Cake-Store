/**
 * DB 只存相对路径（files/download/<category>/<name>），渲染时按当前
 * 环境拼接绝对地址。绝对地址入库会在域名/端口变化时让历史图片全部失效。
 */
export function fileUrl(path) {
    if (!path) return path
    if (/^(https?:)?\/\//i.test(path) || /^(data|blob):/i.test(path)) return path
    const base = (import.meta.env.VITE_BASE_URL || '').replace(/\/+$/, '')
    return `${base}/${String(path).replace(/^\/+/, '')}`
}
