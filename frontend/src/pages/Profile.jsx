import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { authApi } from '../api/auth';
import { 
  User, Calendar, Trophy, LogOut, Mail, Shield, Settings, BarChart3, 
  Zap, Swords, TrendingUp, Table, History 
} from 'lucide-react';

const Profile = () => {
  const { user, logout } = useAuth();
  
  const [stats, setStats] = useState({
    courses_count: 0,
    tasks_solved: 0,
    total_xp: 0
  });
  
  // Стейт для PvP статистики
  const [pvpStats, setPvpStats] = useState({
    current_rating: 1000,
    total_matches: 0,
    wins: 0,
    losses: 0,
    draws: 0,
    win_rate: 0,
    matches_history: []
  });
  
  const [eloHistory, setEloHistory] = useState([]);
  const [loadingPvP, setLoadingPvP] = useState(true);

  // Загружаем основную статистику
  useEffect(() => {
    const fetchPvPStats = async () => {
      try {
        const pvpData = await authApi.getPVpStats(); // ← РЕАЛЬНЫЙ ВЫЗОВ
        setPvpStats(pvpData);
        setEloHistory(pvpData.rating_history || []);
      } catch (e) {
        console.error("Ошибка загрузки PvP статистики", e);
        // fallback на данные из профиля
        setPvpStats(prev => ({
          ...prev,
          current_rating: user?.elo_rating || 1000
        }));
      } finally {
        setLoadingPvP(false);
      }
    };
    
    if (user) fetchPvPStats();
  }, [user]);


  if (!user) return null;

  const joinDate = user.created_at 
    ? new Date(user.created_at).toLocaleDateString('ru-RU') 
    : 'Недавно';

  // Функция открытия админ-панели
  const openAdminPanel = () => {
    window.open('/admin', '_blank', 'noopener,noreferrer');
  };

  // Расчёт цвета рейтинга по системе Elo
  const getRatingColor = (rating) => {
    if (rating >= 1800) return 'text-purple-400'; // Гроссмейстер
    if (rating >= 1600) return 'text-rose-400';   // Мастер
    if (rating >= 1400) return 'text-orange-400';  // Эксперт
    if (rating >= 1200) return 'text-yellow-400';  // Продвинутый
    return 'text-emerald-400'; // Новичок
  };

  // Расчёт цвета для изменения рейтинга
  const getRatingChangeColor = (change) => {
    return change >= 0 ? 'text-green-500' : 'text-red-500';
  };

  return (
    <div className="max-w-6xl mx-auto">
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

              <div className="flex items-center justify-center space-x-2 mb-4">
                 <span className="px-3 py-1 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 text-xs font-bold border border-blue-200 dark:border-blue-800">
                    {user.role === 'admin' ? 'Администратор' : 'Студент'}
                 </span>
                 {user.role === 'admin' && (
                   <button 
                     onClick={openAdminPanel}
                     className="px-3 py-1 rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 text-xs font-bold border border-indigo-200 dark:border-indigo-800 hover:bg-indigo-200 dark:hover:bg-indigo-800 transition-colors"
                     title="Открыть админ-панель"
                   >
                     <Settings size={12} className="inline mr-1" /> Админ
                   </button>
                 )}
              </div>
              
              <div className="mt-4 p-3 bg-gradient-to-r from-amber-50 to-amber-100 dark:from-amber-900/30 dark:to-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
                <div className="flex items-center justify-center mb-1">
                  <Zap className={`mr-2 ${getRatingColor(pvpStats.current_rating)}`} size={18} />
                  <span className="text-xs font-medium text-gray-500 dark:text-gray-400 mr-1">Рейтинг Elo:</span>
                  <span className={`text-2xl font-bold ${getRatingColor(pvpStats.current_rating)}`}>
                    {pvpStats.current_rating}
                  </span>
                </div>
                <div className="text-center mt-1">
                  <span className="text-xs px-2 py-0.5 rounded-full bg-amber-200 dark:bg-amber-800/50 text-amber-800 dark:text-amber-200 font-medium">
                    {pvpStats.current_rating >= 1800 ? 'Гроссмейстер' :
                     pvpStats.current_rating >= 1600 ? 'Мастер' :
                     pvpStats.current_rating >= 1400 ? 'Эксперт' :
                     pvpStats.current_rating >= 1200 ? 'Продвинутый' : 'Новичок'}
                  </span>
                </div>
              </div>
            </div>
            
            <div className="space-y-4 mb-6 text-sm text-gray-600 dark:text-gray-300 border-t dark:border-gray-700 pt-6">
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

        {/* ПРАВАЯ КОЛОНКА: Статистика*/}
        <div className="lg:col-span-2 space-y-6">
           
           {/* Блок с цифрами - ОСНОВНАЯ СТАТИСТИКА
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
           </div> */}

           {/* СТАТИСТИКА ПО СОРЕВНОВАНИЯМ - НОВЫЙ БЛОК ПО ТЗ */}
           <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-xl border border-gray-100 dark:border-gray-700">
             <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center">
                    <Swords className="mr-2 text-rose-500" size={24}/> 
                    Статистика соревнований
                </h2>
                <span className="text-sm text-gray-400">PvP режим</span>
             </div>
             
             <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
               <div className="p-4 rounded-xl text-center bg-amber-50 dark:bg-amber-900/20 border border-amber-100 dark:border-amber-900/50">
                 <div className="text-3xl font-bold text-amber-600 dark:text-amber-400 mb-1">{pvpStats.total_matches}</div>
                 <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Матчей</div>
               </div>
               
               <div className="p-4 rounded-xl text-center bg-green-50 dark:bg-green-900/20 border border-green-100 dark:border-green-900/50">
                 <div className="text-3xl font-bold text-green-600 dark:text-green-400 mb-1">{pvpStats.wins}</div>
                 <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Побед</div>
               </div>
               
               <div className="p-4 rounded-xl text-center bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-900/50">
                 <div className="text-3xl font-bold text-red-600 dark:text-red-400 mb-1">{pvpStats.losses}</div>
                 <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Поражений</div>
               </div>
               
               <div className="p-4 rounded-xl text-center bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-100 dark:border-yellow-900/50">
                 <div className="text-3xl font-bold text-yellow-600 dark:text-yellow-400 mb-1">{pvpStats.draws}</div>
                 <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Ничьих</div>
               </div>
               
               <div className={`p-4 rounded-xl text-center border ${
                 pvpStats.win_rate > 60 ? 'bg-green-50 dark:bg-green-900/20 border-green-100 dark:border-green-900/50' :
                 pvpStats.win_rate > 40 ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-100 dark:border-blue-900/50' :
                 'bg-gray-50 dark:bg-gray-700 border-gray-100 dark:border-gray-600'
               }`}>
                 <div className={`text-3xl font-bold ${
                   pvpStats.win_rate > 60 ? 'text-green-600 dark:text-green-400' :
                   pvpStats.win_rate > 40 ? 'text-blue-600 dark:text-blue-400' : 'text-gray-600 dark:text-gray-300'
                 } mb-1`}>
                   {pvpStats.win_rate}%
                 </div>
                 <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Винрейт</div>
               </div>
             </div>

             {/* ГРАФИК ДИНАМИКИ РЕЙТИНГА - ПО ТЗ */}
             <div className="border-t dark:border-gray-700 pt-6">
               <div className="flex items-center mb-4">
                 <TrendingUp className="text-indigo-500 mr-2" size={20} />
                 <h3 className="text-lg font-bold text-gray-900 dark:text-white">Динамика рейтинга</h3>
               </div>
               {loadingPvP ? (
                 <div className="flex justify-center py-8">
                   <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                 </div>
               ) : eloHistory.length > 0 ? (
                 <div className="grid grid-cols-2 md:grid-cols-5 gap-2 p-3 bg-gray-50 dark:bg-gray-700/20 rounded-lg">
                   {eloHistory.map((point, idx) => (
                     <div key={idx} className="text-center">
                       <div className={`text-lg font-bold ${getRatingColor(point.rating)}`}>
                         {point.rating}
                       </div>
                       <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">{point.date}</div>
                       {idx < eloHistory.length - 1 && (
                         <div className={`h-1 mt-2 rounded-full ${
                           eloHistory[idx+1].rating > point.rating 
                             ? 'bg-green-500' 
                             : eloHistory[idx+1].rating < point.rating 
                             ? 'bg-red-500' 
                             : 'bg-gray-400'
                         }`} />
                       )}
                     </div>
                   ))}
                 </div>
               ) : (
                 <div className="text-center py-6 text-gray-500 dark:text-gray-400">
                   <History className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                   <p>Сыграйте первый матч, чтобы увидеть динамику рейтинга</p>
                 </div>
               )}
             </div>
           </div>

           {/* ИСТОРИЯ МАТЧЕЙ - ТАБЛИЦА ПО ТЗ */}
           <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-xl border border-gray-100 dark:border-gray-700">
             <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center">
                    <Table className="mr-2 text-indigo-500" size={24}/> 
                    История матчей
                </h2>
                <span className="text-sm text-gray-400">{pvpStats.matches_history.length} последних</span>
             </div>
             
             {pvpStats.matches_history.length > 0 ? (
               <div className="overflow-x-auto">
                 <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                   <thead className="bg-gray-50 dark:bg-gray-700/50">
                     <tr>
                       <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Дата</th>
                       <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Соперник</th>
                       <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Счёт</th>
                       <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Результат</th>
                       <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Изменение</th>
                     </tr>
                   </thead>
                   <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                     {pvpStats.matches_history.map((match) => (
                       <tr key={match.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                         <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">{match.date}</td>
                         <td className="px-4 py-3 whitespace-nowrap">
                           <div className="flex items-center">
                             <div className="w-2 h-2 rounded-full bg-indigo-500 mr-2"></div>
                             <span className="text-gray-900 dark:text-white font-medium">{match.opponent}</span>
                           </div>
                         </td>
                         <td className="px-4 py-3 whitespace-nowrap text-sm font-mono font-medium text-gray-800 dark:text-gray-200">{match.score}</td>
                         <td className="px-4 py-3 whitespace-nowrap">
                           <span className={`px-2.5 py-0.5 inline-flex text-xs font-medium rounded-full ${
                             match.result === 'win' 
                               ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' 
                               : match.result === 'loss'
                               ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
                               : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300'
                           }`}>
                             {match.result === 'win' ? 'Победа' : match.result === 'loss' ? 'Поражение' : 'Ничья'}
                           </span>
                         </td>
                         <td className={`px-4 py-3 whitespace-nowrap text-sm font-bold ${
                           getRatingChangeColor(match.rating_change)
                         }`}>
                           {match.rating_change >= 0 ? '+' : ''}{match.rating_change}
                         </td>
                       </tr>
                     ))}
                   </tbody>
                 </table>
               </div>
             ) : (
               <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                 <Swords className="w-12 h-12 mx-auto mb-3 text-gray-400 opacity-50" />
                 <p className="font-medium">Ещё нет сыгранных матчей</p>
                 <p className="text-sm mt-1">Начните соревноваться в режиме PvP, чтобы увидеть историю</p>
               </div>
             )}
           </div>
        </div>
      </div>
    </div>
  );
};

export default Profile;