import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Brain, LogIn, ArrowRight } from 'lucide-react';
import { motion } from 'framer-motion';

const Landing = () => {
  const navigate = useNavigate();

  return (
    <div className="max-w-4xl mx-auto text-center py-12">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        <div className="inline-block p-4 rounded-2xl mb-6 bg-indigo-500/10">
          <Brain className="w-12 h-12 text-indigo-400" />
        </div>
        <h1 className="text-3xl md:text-4xl lg:text-5xl font-bold mb-8 bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-cyan-400">
          predprof edu
        </h1>
        <div className="flex flex-col sm:flex-row justify-center gap-4">
          <button
            onClick={() => navigate('/login')}
            className="flex items-center justify-center space-x-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-3 px-8 rounded-xl transition-all transform hover:scale-105"
          >
            <LogIn size={20} />
            <span>Войти</span>
          </button>
          <button
            onClick={() => navigate('/register')}
            className="flex items-center justify-center space-x-2 font-medium py-3 px-8 rounded-xl transition-all transform hover:scale-105 bg-white dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-800 dark:text-white border border-gray-300 dark:border-gray-700"
          >
            <ArrowRight size={20} />
            <span>Регистрация</span>
          </button>
        </div>
      </motion.div>
    </div>
  );
};

export default Landing;