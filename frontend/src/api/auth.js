import axiosClient from './axiosClient';

export const authApi = {
  // Логин (x-www-form-urlencoded)
  login: async (email, password) => {
    const formData = new URLSearchParams();
    formData.append('username', email); // FastAPI OAuth2 ожидает поле username
    formData.append('password', password);

    const response = await axiosClient.post('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    return response.data; // Возвращает { access_token, token_type }
  },

  // Регистрация (JSON)
  // Имя принимаем, но в бек пока не шлем, т.к. нет поля в БД
  register: async (email, password, name) => {
    const response = await axiosClient.post('/auth/register', {
      email,
      password,
      // is_active: true,
      // is_superuser: false,
    });
    return response.data;
  },

  // Получение текущего юзера
  getMe: async () => {
    const response = await axiosClient.get('/auth/me');
    return response.data;
  },

  getStats: async () => {
    const response = await axiosClient.get('/auth/stats');
    return response.data;
  },

  getPVpStats: async () => {
    const response = await axiosClient.get('/pvp/stats');
    return response.data;
  },
};