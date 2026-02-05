import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation, Link } from 'react-router-dom'; // Добавил Link
import { AuthProvider, useAuth } from './context/AuthContext';
import { Sun, Moon, LogOut, BookOpen, User, Swords } from 'lucide-react'; // Добавил иконку Swords для PVP

import LandingPage from './pages/Landing';
import LoginPage from './pages/Login';
import RegisterPage from './pages/Register';
import Dashboard from './pages/Dashboard';
import CourseDetail from './pages/CourseDetail';
import Profile from './pages/Profile';
import PVPGame from './pages/PVPGame'; // Новая страница

const ProtectedRoute = ({ children }) => {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return children;
};

const Layout = () => {
  const { user, logout } = useAuth();
  const [theme, setTheme] = useState('dark');
  const location = useLocation();

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
  }, [theme]);

  const isLanding = location.pathname === '/';

  return (
    <div className={`min-h-screen transition-colors duration-300 ${theme === 'dark' ? 'bg-gray-900 text-gray-100' : 'bg-gray-50 text-gray-900'}`}>
      <header className={`sticky top-0 z-50 border-b ${theme === 'dark' ? 'border-gray-800 bg-gray-900/80' : 'border-gray-200 bg-white/80'} backdrop-blur-lg`}>
        <div className="container mx-auto px-4 py-3 flex justify-between items-center">
          <Link to="/" className="flex items-center space-x-2 cursor-pointer">
            <h1 className="text-xl md:text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-cyan-400">
              PredProf Olympyad
            </h1>
          </Link>
          
          <div className="flex items-center space-x-4">
            {/* Меню для авторизованных пользователей */}
            {user && (
              <div className="hidden md:flex items-center space-x-1">
                <Link to="/courses" className={`flex items-center space-x-1 px-3 py-1.5 rounded-lg transition-colors ${location.pathname.includes('/courses') ? 'bg-indigo-500/10 text-indigo-400' : 'hover:bg-gray-800'}`}>
                  <BookOpen size={18} />
                  <span>Курсы</span>
                </Link>
                <Link to="/pvp" className={`flex items-center space-x-1 px-3 py-1.5 rounded-lg transition-colors ${location.pathname.includes('/pvp') ? 'bg-indigo-500/10 text-indigo-400' : 'hover:bg-gray-800'}`}>
                  <Swords size={18} />
                  <span>Дуэли</span>
                </Link>
                <Link to="/profile" className={`flex items-center space-x-1 px-3 py-1.5 rounded-lg transition-colors ${location.pathname === '/profile' ? 'bg-indigo-500/10 text-indigo-400' : 'hover:bg-gray-800'}`}>
                  <User size={18} />
                  <span>Профиль</span>
                </Link>
              </div>
            )}

            <button
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              className="p-2 rounded-full transition-colors hover:bg-gray-700/50"
            >
              {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
            </button>
            
            {user ? (
              <button onClick={logout} className="p-2 rounded-lg hover:bg-red-500/10 text-red-400" title="Выход">
                <LogOut size={20} />
              </button>
            ) : (
              !isLanding && (
                <Link to="/login" className="text-indigo-400 font-medium hover:text-indigo-300">Войти</Link>
              )
            )}
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <Routes>
          <Route path="/" element={user ? <Navigate to="/courses" /> : <LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          
          <Route path="/courses" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/course/:id" element={<ProtectedRoute><CourseDetail /></ProtectedRoute>} />
          <Route path="/pvp" element={<ProtectedRoute><PVPGame /></ProtectedRoute>} />
          <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
          
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
};

const App = () => {
  return (
    <Router>
      <AuthProvider>
        <Layout />
      </AuthProvider>
    </Router>
  );
};

export default App;