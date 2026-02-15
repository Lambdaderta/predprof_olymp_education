import axios from 'axios';

const axiosClient = axios.create({
  baseURL: '/api/v1', // Адрес твоего FastAPI (через reverse proxy)
  headers: {
    'Content-Type': 'application/json',
  },
});

// Интерцептор запросов: добавляем токен, если он есть
axiosClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Интерцептор ответов: если 401 (Unauthorized), разлогиниваем (или можно добавить логику refresh)
axiosClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response && error.response.status === 401) {
      // Если токен протух, удаляем его и редиректим на логин
      // В будущем тут можно сделать логику refresh token
      localStorage.removeItem('access_token');
      // window.location.href = '/login'; // Можно включить жесткий редирект
    }
    return Promise.reject(error);
  }
);

export default axiosClient;