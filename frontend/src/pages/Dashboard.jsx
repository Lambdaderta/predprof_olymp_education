import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Star, BarChart3, CheckCircle, GraduationCap, Brain, BookOpen } from 'lucide-react';
import { motion } from 'framer-motion';
import { coursesApi } from '../api/courses';

const Dashboard = () => {
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchCourses = async () => {
      try {
        const data = await coursesApi.getAll();
        setCourses(data);
      } catch (error) {
        console.error("Failed to fetch courses", error);
      } finally {
        setLoading(false);
      }
    };
    fetchCourses();
  }, []);

  const getLevelColor = (level) => {
    switch(level) {
      case 'Начальный': return 'bg-green-500/10 text-green-600 dark:text-green-400';
      case 'Средний': return 'bg-blue-500/10 text-blue-600 dark:text-blue-400';
      case 'Продвинутый': return 'bg-purple-500/10 text-purple-600 dark:text-purple-400';
      default: return 'bg-gray-500/10 text-gray-600 dark:text-gray-400';
    }
  };

  const getProgressColor = (progress) => {
    if (progress > 80) return 'bg-green-500';
    if (progress > 50) return 'bg-yellow-500';
    return 'bg-blue-500';
  };

  if (loading) {
    return <div className="flex justify-center py-20"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500"></div></div>;
  }

  return (
    <div>
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 gap-4">
        <div>
          <h2 className="text-2xl md:text-3xl font-bold text-gray-900 dark:text-white">Доступные курсы</h2>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Начните обучение или продолжите изучение материалов</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {courses.map((course) => (
          <motion.div
            key={course.id}
            whileHover={{ y: -5 }}
            className="rounded-2xl overflow-hidden shadow-lg cursor-pointer transition-all bg-white dark:bg-gray-800 hover:shadow-xl dark:hover:bg-gray-700/50"
            onClick={() => navigate(`/course/${course.id}`)}
          >
            <div className="p-6">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <span className={`text-xs font-medium px-2 py-1 rounded-full ${getLevelColor(course.level)}`}>
                    {course.level}
                  </span>
                </div>
                <Star className="text-yellow-400" size={20} />
              </div>
              <h3 className="text-xl font-bold mb-2 text-gray-900 dark:text-white">{course.title}</h3>
              <p className="text-gray-500 dark:text-gray-400 mb-4 line-clamp-2">{course.description}</p>
              
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between text-sm mb-1 text-gray-700 dark:text-gray-300">
                    <span>Прогресс</span>
                    <span>{course.progress}%</span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
                    <div 
                      className={`h-full rounded-full transition-all ${getProgressColor(course.progress)}`}
                      style={{ width: `${course.progress}%` }}
                    ></div>
                  </div>
                </div>
                
                {course.averageScore > 0 && (
                  <div className="flex items-center text-gray-700 dark:text-gray-300">
                    <BarChart3 className="text-indigo-400 mr-2" size={16} />
                    <span className="text-sm">Средний балл: {course.averageScore}%</span>
                  </div>
                )}
                
                <button className="w-full flex items-center justify-center space-x-2 py-2 bg-indigo-50 dark:bg-indigo-600/10 text-indigo-600 dark:text-indigo-400 rounded-lg hover:bg-indigo-100 dark:hover:bg-indigo-600/20 transition-colors">
                  <CheckCircle size={18} />
                  <span>Проверить уровень</span>
                </button>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default Dashboard;