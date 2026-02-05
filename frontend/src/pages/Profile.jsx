import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { authApi } from '../api/auth';
import { User, Calendar, Trophy, LogOut, Mail, Shield } from 'lucide-react';

const Profile = () => {
  const { user, logout } = useAuth();
  
  // Стейт для статистики
  const [stats, setStats] = useState({
    courses_count: 0,
    tasks_solved: 0,
    total_xp: 0
  });

  // Загружаем статистику при открытии
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await authApi.getStats();
        setStats(data);
      } catch (e) {
        console.error("Ошибка загрузки статистики", e);
      }
    };
    fetchStats();
  }, []);

  if (!user) return null;

  // Форматируем дату регистрации (если есть) или текущую дату
  const joinDate = user.created_at 
    ? new Date(user.created_at).toLocaleDateString('ru-RU') 
    : 'Недавно';

  return (
    <div className="max-w-5xl mx-auto">
      {/* Заголовок */}
      <div className="flex items-center mb-8">
        <div className="bg-indigo-500/10 p-3 rounded-xl mr-4">
          <User className="w-8 h-8 text-indigo-500" />
        </div>
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-gray-900 dark:text-white">Личный кабинет</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Управление аккаунтом и статистика</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* ЛЕВАЯ КОЛОНКА: Карточка пользователя */}
        <div className="lg:col-span-1">
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-xl border border-gray-100 dark:border-gray-700 h-full flex flex-col">
            <div className="text-center mb-6 flex-grow">
              {/* Аватарка из инициалов */}
              <div className="w-24 h-24 rounded-full mx-auto flex items-center justify-center text-3xl font-bold bg-gradient-to-br from-indigo-500 to-purple-600 text-white mb-4 shadow-lg">
                {user.name ? user.name.charAt(0).toUpperCase() : 'U'}
              </div>
              
              <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-1">
                {user.name || 'Пользователь'}
              </h3>
              
              <div className="flex items-center justify-center text-gray-500 dark:text-gray-400 text-sm mb-4">
                <Mail size={14} className="mr-1.5" />
                {user.email}
              </div>

              <div className="flex items-center justify-center space-x-2">
                 <span className="px-3 py-1 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 text-xs font-bold border border-blue-200 dark:border-blue-800">
                    {user.role === 'admin' ? 'Администратор' : 'Студент'}
                 </span>
              </div>
            </div>
            
            <div className="space-y-4 mb-8 text-sm text-gray-600 dark:text-gray-300 border-t dark:border-gray-700 pt-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                    <Calendar className="text-indigo-400 mr-3" size={18} />
                    <span>Дата регистрации</span>
                </div>
                <span className="font-medium">{joinDate}</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                    <Shield className="text-green-400 mr-3" size={18} />
                    <span>Статус аккаунта</span>
                </div>
                <span className="text-green-500 font-medium">Активен</span>
              </div>
            </div>

            <button 
              onClick={logout}
              className="w-full flex items-center justify-center space-x-2 border border-red-200 dark:border-red-900 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 py-3 rounded-xl transition-colors font-medium mt-auto"
            >
              <LogOut size={18} />
              <span>Выйти из аккаунта</span>
            </button>
          </div>
        </div>

        {/* ПРАВАЯ КОЛОНКА: Статистика */}
        <div className="lg:col-span-2 space-y-6">
           
           {/* Блок с цифрами */}
           <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-xl border border-gray-100 dark:border-gray-700">
             <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center">
                    <Trophy className="mr-2 text-yellow-500" size={24}/> 
                    Достижения
                </h2>
                <span className="text-sm text-gray-400">Обновляется в реальном времени</span>
             </div>
             
             <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
               <div className="p-4 rounded-xl text-center bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-100 dark:border-indigo-900/50">
                 <div className="text-3xl font-bold text-indigo-600 dark:text-indigo-400 mb-1">{stats.courses_count}</div>
                 <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Курсов</div>
               </div>
               
               <div className="p-4 rounded-xl text-center bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-900/50">
                 <div className="text-3xl font-bold text-blue-600 dark:text-blue-400 mb-1">0</div> 
                 <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Часов</div>
               </div>
               
               <div className="p-4 rounded-xl text-center bg-green-50 dark:bg-green-900/20 border border-green-100 dark:border-green-900/50">
                 <div className="text-3xl font-bold text-green-600 dark:text-green-400 mb-1">{stats.tasks_solved}</div>
                 <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Задач</div>
               </div>
               
               <div className="p-4 rounded-xl text-center bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-100 dark:border-yellow-900/50">
                 <div className="text-3xl font-bold text-yellow-600 dark:text-yellow-400 mb-1">{stats.total_xp}</div>
                 <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">XP</div>
               </div>
             </div>
           </div>

           {/* Заглушка для будущих графиков */}
           <div className="bg-white dark:bg-gray-800 rounded-2xl p-8 shadow-xl border border-gray-100 dark:border-gray-700 text-center">
              <div className="inline-block p-4 rounded-full bg-gray-100 dark:bg-gray-700 mb-4">
                  <BarChart3 className="w-8 h-8 text-gray-400" />
              </div>
              <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">График активности</h3>
              <p className="text-gray-500 dark:text-gray-400 max-w-md mx-auto">
                  Здесь скоро появится график вашей учебной активности по дням недели. Продолжайте решать задачи!
              </p>
           </div>
        </div>
      </div>
    </div>
  );
};

// Не забываем импортировать BarChart3, если его нет в imports
import { BarChart3 } from 'lucide-react';

export default Profile;