import React, { createContext, useState, useEffect, useContext } from 'react';
import { authApi } from '../api/auth';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  // 1. Инициализируем токен сразу из localStorage
  const [token, setToken] = useState(localStorage.getItem('access_token'));
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Проверка токена при загрузке страницы
  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem('access_token');
      
      if (storedToken) {
        setToken(storedToken); // Синхронизируем стейт
        try {
          const userData = await authApi.getMe();
          const displayName = userData.email.split('@')[0]; 
          setUser({ ...userData, name: displayName });
        } catch (error) {
          console.error("Ошибка проверки сессии:", error);
          localStorage.removeItem('access_token');
          setToken(null);
        }
      } else {
          setToken(null);
      }
      setLoading(false);
    };
    initAuth();
  }, []);

  const login = async (email, password) => {
    const data = await authApi.login(email, password);
    
    // Сохраняем и в localStorage, и в стейт
    localStorage.setItem('access_token', data.access_token);
    setToken(data.access_token);
    
    const userData = await authApi.getMe();
    const displayName = userData.email.split('@')[0];
    setUser({ ...userData, name: displayName });
    return userData;
  };

  const register = async (name, email, password) => {
    await authApi.register(email, password, name);
    return login(email, password);
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    setToken(null); // Очищаем стейт
    setUser(null);
  };

  return (
    // 2. ВАЖНО: Передаем token в value
    <AuthContext.Provider value={{ user, token, login, register, logout, loading }}>
      {!loading && children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);