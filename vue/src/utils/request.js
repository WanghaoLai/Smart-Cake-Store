import { ElMessage } from 'element-plus'
import router from '../router'
import axios from "axios";

const request = axios.create({
    baseURL: import.meta.env.VITE_BASE_URL,
    timeout: 30000  // 后台接口超时时间设置
})

// request 拦截器
// 可以自请求发送前对请求做一些处理
request.interceptors.request.use(config => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config
}, error => {
    return Promise.reject(error)
});

// response 拦截器
// 可以在接口响应后统一处理结果
request.interceptors.response.use(
    response => {
        let res = response.data;
        // 如果是返回的文件
        if (response.config.responseType === 'blob') {
            return res
        }
        // 兼容服务端返回的字符串数据；非 JSON 字符串直接透传，避免未捕获异常
        if (typeof res === 'string' && res) {
            try {
                res = JSON.parse(res)
            } catch (e) {
                console.warn('响应不是合法 JSON，按原文处理:', res)
            }
        }
        // 当权限验证不通过的时候给出提示
        if (res.code === '401') {
            ElMessage.error(res.msg);
            router.push("/login")
        }
        return res;
    },
        error => {
            if (error.response && error.response.status === 401) {
                ElMessage.error('登录已过期，请重新登录');
                localStorage.removeItem('token');
                localStorage.removeItem('system-user');
                router.push('/login');
            }
            console.error('请求失败:', error)
            return Promise.reject(error)
        }
)


export default request
