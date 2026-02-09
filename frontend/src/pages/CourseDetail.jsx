import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, BookOpen, CheckCircle, BarChart3, StopCircle, 
  Volume2, Brain, Hash, Lightbulb, ChevronDown, ChevronUp, 
  Check, X, FileText, Play, Loader2
} from 'lucide-react';
import { coursesApi } from '../api/courses';
import MarkdownRenderer from '../components/MarkdownRenderer';

const CourseDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  
  const [course, setCourse] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Навигация
  const [viewMode, setViewMode] = useState('overview'); 
  const [selectedLecture, setSelectedLecture] = useState(null);
  const [selectedTask, setSelectedTask] = useState(null);
  const [expandedLectures, setExpandedLectures] = useState({});

  // Состояния ответов
  // userAnswers[taskId] = { answer: "...", solution: "...", isCorrect: boolean }
  const [userAnswers, setUserAnswers] = useState({});
  const [showExplanation, setShowExplanation] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  
  // Состояние генерации новой задачи
  const [generating, setGenerating] = useState(false);
  
  useEffect(() => {
    const loadCourse = async () => {
      const data = await coursesApi.getById(id);
      if (data) {
        setCourse(data);
        
        // --- НОВАЯ ЛОГИКА ---
        // Проходимся по всем лекциям и задачам, находим решенные (is_solved)
        // и заранее заполняем userAnswers, чтобы они горели зеленым
        const initialAnswers = {};
        data.lectures.forEach(lecture => {
            lecture.tasks.forEach(task => {
                if (task.is_solved) {
                    initialAnswers[task.id] = {
                        answer: String(task.correctAnswer), // Или заглушка, т.к. мы не знаем что ответил юзер, если бек не вернул
                        isCorrect: true,
                        solution: ''
                    };
                }
            });
        });
        setUserAnswers(initialAnswers);
        // --------------------
        
      } else {
        navigate('/courses');
      }
      setLoading(false);
    };
    loadCourse();
    return () => window.speechSynthesis.cancel();
  }, [id, navigate]);

  // --- Хелперы ---

  const toggleLectureExpand = (lectureId, e) => {
    e.stopPropagation();
    setExpandedLectures(prev => ({ ...prev, [lectureId]: !prev[lectureId] }));
  };

  const handleLectureSelect = (lecture) => {
    setSelectedLecture(lecture);
    setViewMode('lecture');
    window.scrollTo(0, 0);
  };

  const handleTaskSelect = (task) => {
    setSelectedTask(task);
    setViewMode('task');
    // Сбрасываем показ объяснения при входе в задачу, если она еще не решена
    // Если решена (есть в userAnswers), то можно показать, если юзер сам захочет
    setShowExplanation(false);
    window.scrollTo(0, 0);
  };

  // Обработчик генерации похожей задачи
  const handleGenerateSimilar = async () => {
    if (!selectedTask) return;
    
    setGenerating(true);
    
    try {
      // Генерируем новую задачу
      const newTask = await coursesApi.generateSimilarTask(selectedTask.id);
      
      // Обновляем выбранную задачу
      setSelectedTask(newTask);
      
      // Сбрасываем состояние ответа для новой задачи
      setUserAnswers(prev => ({
        ...prev,
        [newTask.id]: { answer: '', isCorrect: undefined, solution: '' }
      }));
      
      // Скрываем объяснение
      setShowExplanation(false);
      
      // Скролл вверх к новой задаче
      window.scrollTo({ top: 0, behavior: 'smooth' });
      
    } catch (error) {
      alert("Не удалось сгенерировать задачу. Попробуйте позже.");
      console.error("Generation error:", error);
    } finally {
      setGenerating(false);
    }
  };

  // Универсальная функция проверки
  const checkAnswer = (taskId, type, value, extraData = {}) => {
    const task = selectedTask; // или искать по taskId в списке
    let isCorrect = false;

    if (type === 'multiple-choice') {
        isCorrect = (value === task.correctAnswer);
    } else {
        // Для numeric и open сравниваем строки
        const userNorm = String(value).trim().replace(',', '.').toLowerCase();
        const correctNorm = String(task.correctAnswer).trim().replace(',', '.').toLowerCase();
        isCorrect = userNorm === correctNorm;
    }

    setUserAnswers(prev => ({
      ...prev,
      [taskId]: { 
          answer: value, 
          isCorrect,
          solution: extraData.solution || '' 
      }
    }));
    
    coursesApi.submitTask(taskId, value, isCorrect);
  };

  const speakText = (text) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const cleanText = text.replace(/[#*`_]/g, '');
      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.lang = 'ru-RU';
      window.speechSynthesis.speak(utterance);
      setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
    }
  };

  const stopSpeaking = () => {
    window.speechSynthesis.cancel();
    setIsSpeaking(false);
  };

  if (loading) return <div className="flex justify-center items-center h-screen"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div></div>;
  if (!course) return null;

  // --- Рендеринг инпутов задач ---

  const renderTaskInput = () => {
    const task = selectedTask;
    const answerData = userAnswers[task.id];
    const userAnswer = answerData?.answer || '';
    const userSolution = answerData?.solution || ''; // Для open задач
    const isAnswered = answerData?.isCorrect !== undefined;

    // 1. ЧИСЛОВОЙ ОТВЕТ (Numeric)
    if (task.type === 'numeric') {
        return (
          <div className="space-y-4">
            <input
              type="text"
              value={userAnswer}
              disabled={isAnswered && answerData.isCorrect}
              onChange={(e) => {
                  // Обновляем локально без проверки (проверка по кнопке)
                  setUserAnswers(prev => ({ ...prev, [task.id]: { ...prev[task.id], answer: e.target.value } }));
              }}
              className={`w-full px-4 py-3 rounded-lg border outline-none font-mono text-lg transition-all ${
                 isAnswered 
                    ? (answerData.isCorrect 
                        ? "bg-green-50 dark:bg-green-900/20 border-green-500 text-green-700 dark:text-green-400" 
                        : "bg-red-50 dark:bg-red-900/20 border-red-500 text-red-700 dark:text-red-400")
                    : "bg-gray-50 dark:bg-gray-700 border-gray-300 dark:border-gray-600 focus:ring-indigo-500 focus:border-indigo-500 text-gray-900 dark:text-white"
              }`}
              placeholder="Введите числовой ответ"
              onKeyDown={(e) => e.key === 'Enter' && checkAnswer(task.id, 'numeric', userAnswer)}
            />
            <div className="flex justify-between items-center">
                {isAnswered && (
                    <span className={`font-medium ${answerData.isCorrect ? 'text-green-500' : 'text-red-500'}`}>
                        {answerData.isCorrect ? 'Верно!' : 'Неверно, попробуйте еще раз'}
                    </span>
                )}
                <button
                    onClick={() => checkAnswer(task.id, 'numeric', userAnswer)}
                    className="ml-auto px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors"
                >
                    Проверить
                </button>
            </div>
          </div>
        );
    }

    // 2. ВЫБОР ОТВЕТА (Multiple Choice)
    if (task.type === 'multiple-choice') {
        return (
          <div className="space-y-3">
            {task.options.map((option, index) => {
              const isSelected = userAnswer === index;
              let itemClass = 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700';
              let badgeClass = 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300';
              
              if (isSelected && isAnswered) {
                  if (answerData.isCorrect) {
                      itemClass = 'bg-green-50 dark:bg-green-900/30 border-green-500';
                      badgeClass = 'bg-green-500 text-white';
                  } else {
                      itemClass = 'bg-red-50 dark:bg-red-900/30 border-red-500';
                      badgeClass = 'bg-red-500 text-white';
                  }
              }

              return (
                <button
                  key={index}
                  onClick={() => checkAnswer(task.id, 'multiple-choice', index)}
                  disabled={isAnswered && answerData.isCorrect}
                  className={`w-full text-left p-4 rounded-xl border transition-all flex items-start ${itemClass}`}
                >
                  <div className={`w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center mr-3 mt-0.5 transition-colors ${badgeClass}`}>
                    {isSelected && isAnswered ? (
                      answerData.isCorrect ? <Check size={14} /> : <X size={14} />
                    ) : String.fromCharCode(65 + index)}
                  </div>
                  <div className="text-gray-800 dark:text-gray-200 w-full">
                      <MarkdownRenderer content={option} className="prose-p:mb-0" />
                  </div>
                </button>
              );
            })}
          </div>
        );
    }

    // 3. ОТКРЫТЫЙ ОТВЕТ (Open - с двумя полями)
    if (task.type === 'open') {
        return (
          <div className="space-y-6">
            {/* Поле для решения (не проверяется автоматически) */}
            <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Ход решения (черновик):
                </label>
                <textarea
                  rows={6}
                  value={userSolution}
                  onChange={(e) => setUserAnswers(prev => ({
                    ...prev,
                    [task.id]: { ...prev[task.id], solution: e.target.value }
                  }))}
                  className="w-full px-4 py-3 rounded-lg border bg-gray-50 dark:bg-gray-700 border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white focus:ring-indigo-500 focus:border-indigo-500 outline-none resize-none font-sans"
                  placeholder="Запишите здесь ваши рассуждения..."
                />
            </div>

            {/* Поле для финального ответа (проверяется) */}
            <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Финальный ответ (число или слово):
                </label>
                <div className="flex gap-4">
                    <input
                      type="text"
                      value={userAnswer}
                      disabled={isAnswered && answerData.isCorrect}
                      onChange={(e) => setUserAnswers(prev => ({
                        ...prev,
                        [task.id]: { ...prev[task.id], answer: e.target.value }
                      }))}
                      className={`flex-grow px-4 py-3 rounded-lg border outline-none transition-all font-mono ${
                         isAnswered 
                            ? (answerData.isCorrect 
                                ? "bg-green-50 dark:bg-green-900/20 border-green-500 text-green-700 dark:text-green-400" 
                                : "bg-red-50 dark:bg-red-900/20 border-red-500 text-red-700 dark:text-red-400")
                            : "bg-gray-50 dark:bg-gray-700 border-gray-300 dark:border-gray-600 focus:ring-indigo-500 focus:border-indigo-500 text-gray-900 dark:text-white"
                      }`}
                      placeholder="Ответ"
                      onKeyDown={(e) => e.key === 'Enter' && checkAnswer(task.id, 'open', userAnswer, { solution: userSolution })}
                    />
                    <button
                        onClick={() => checkAnswer(task.id, 'open', userAnswer, { solution: userSolution })}
                        disabled={!userAnswer.trim()}
                        className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
                    >
                        Проверить
                    </button>
                </div>
                {isAnswered && (
                    <div className={`mt-2 font-medium ${answerData.isCorrect ? 'text-green-500' : 'text-red-500'}`}>
                        {answerData.isCorrect ? 'Ответ верный! Решение сохранено.' : 'Ответ не сходится с эталоном. Проверьте вычисления.'}
                    </div>
                )}
            </div>
          </div>
        );
    }
    
    return <div className="text-gray-500">Тип задачи не поддерживается</div>;
  };


  if (viewMode === 'lecture' && selectedLecture) {
    return (
      <div>
        <div className="flex items-center mb-6 cursor-pointer text-gray-600 dark:text-gray-400 hover:text-indigo-500 transition-colors" 
             onClick={() => setViewMode('overview')}>
          <ArrowLeft className="mr-2" size={20} />
          <span className="font-medium">К плану курса</span>
        </div>
        
        <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 md:p-8 shadow-xl border border-gray-100 dark:border-gray-700">
          <div className="flex justify-between items-start mb-6 border-b dark:border-gray-700 pb-4">
            <h3 className="text-2xl font-bold text-gray-900 dark:text-white">{selectedLecture.lecture_name || selectedLecture.title}</h3>
            <button
              onClick={() => isSpeaking ? stopSpeaking() : speakText(selectedLecture.content)}
              className="p-2 rounded-lg text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              {isSpeaking ? <StopCircle size={24} className="text-red-500" /> : <Volume2 size={24} />}
            </button>
          </div>
          
          <MarkdownRenderer content={selectedLecture.content} />
          
          {selectedLecture.tasks?.length > 0 && (
             <div className="mt-10 pt-6 border-t dark:border-gray-700">
                <h4 className="text-lg font-bold mb-4 text-gray-900 dark:text-white">Закрепление материала:</h4>
                <div className="grid grid-cols-1 gap-3">
                   {selectedLecture.tasks.map((task, idx) => {
                       const isDone = userAnswers[task.id]?.isCorrect;
                       return (
                          <button
                            key={task.id}
                            onClick={() => handleTaskSelect(task)}
                            className={`flex items-center p-3 rounded-lg transition-colors text-left border ${
                                isDone 
                                ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
                                : 'bg-indigo-50 dark:bg-indigo-900/20 hover:bg-indigo-100 dark:hover:bg-indigo-900/40 border-transparent'
                            }`}
                          >
                             <div className={`w-6 h-6 rounded flex items-center justify-center text-xs mr-3 font-bold ${
                                 isDone 
                                 ? 'bg-green-200 dark:bg-green-800 text-green-700 dark:text-green-300'
                                 : 'bg-indigo-200 dark:bg-indigo-800 text-indigo-700 dark:text-indigo-300'
                             }`}>
                               {isDone ? <Check size={14}/> : idx + 1}
                             </div>
                             <span className={`${isDone ? 'text-green-900 dark:text-green-100' : 'text-indigo-900 dark:text-indigo-100'} font-medium`}>
                                {task.type === 'open' ? 'Открытый вопрос' : 'Задача'}
                             </span>
                          </button>
                       );
                   })}
                </div>
             </div>
          )}
        </div>
      </div>
    );
  }

  if (viewMode === 'task' && selectedTask) {
    const isAnswered = userAnswers[selectedTask.id]?.isCorrect !== undefined;

    return (
      <div>
        <div className="flex items-center mb-6 cursor-pointer text-gray-600 dark:text-gray-400 hover:text-indigo-500 transition-colors" 
             onClick={() => setViewMode('overview')}>
          <ArrowLeft className="mr-2" size={20} />
          <span className="font-medium">Вернуться к списку</span>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 md:p-8 shadow-xl border border-gray-100 dark:border-gray-700">
           <div className="flex items-center mb-4">
              <span className="bg-indigo-100 dark:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400 p-2 rounded-lg mr-3">
                  {selectedTask.type === 'numeric' && <Hash size={20} />}
                  {selectedTask.type === 'multiple-choice' && <CheckCircle size={20} />}
                  {selectedTask.type === 'open' && <FileText size={20} />}
              </span>
              <h3 className="text-xl font-bold text-gray-900 dark:text-white">Задание</h3>
           </div>
           
           <div className="mb-8 text-lg text-gray-800 dark:text-gray-200 bg-gray-50 dark:bg-gray-700/30 p-5 rounded-xl border border-gray-100 dark:border-gray-600">
              <MarkdownRenderer content={selectedTask.question} className="prose-p:mb-0" />
           </div>
           
           {renderTaskInput()}

           {/* Кнопки после решения */}
           <div className="flex justify-between mt-8 border-t dark:border-gray-700 pt-4">
              {/* Кнопка генерации */}
              {isAnswered && (
                <button
                  onClick={handleGenerateSimilar}
                  disabled={generating}
                  className="flex items-center px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {generating ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Генерируем...
                    </>
                  ) : (
                    <>
                      <Lightbulb className="mr-2 h-4 w-4" />
                      Ещё задача
                    </>
                  )}
                </button>
              )}
              
              {/* Кнопка объяснения */}
              {isAnswered ? (
                <button 
                  onClick={() => setShowExplanation(!showExplanation)}
                  className="flex items-center text-indigo-500 hover:text-indigo-600 font-medium transition-colors"
                >
                  <Brain size={18} className="mr-2" />
                  {showExplanation ? 'Скрыть объяснение' : 'Показать объяснение'}
                </button>
              ) : (
                <div className="text-sm text-gray-400 italic">
                  Решите задачу, чтобы увидеть объяснение.
                </div>
              )}
           </div>

           {showExplanation && selectedTask.explanation && (
             <div className="mt-4 p-5 bg-indigo-50 dark:bg-indigo-900/20 rounded-xl border border-indigo-100 dark:border-indigo-900/50">
               <h4 className="font-bold text-indigo-900 dark:text-indigo-200 mb-2 flex items-center">
                   <Brain size={18} className="mr-2"/> Пояснение:
               </h4>
               <MarkdownRenderer content={selectedTask.explanation} />
             </div>
           )}
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center mb-6 cursor-pointer text-gray-600 dark:text-gray-400 hover:text-indigo-500" onClick={() => navigate('/courses')}>
        <ArrowLeft className="mr-2" size={20} />
        <span className="font-medium">К списку курсов</span>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 md:p-8 mb-8 shadow-xl border border-gray-100 dark:border-gray-700">
        <div className="flex flex-col md:flex-row justify-between mb-6">
          <div>
            <div className="flex items-center space-x-3 mb-2">
                <span className="text-xs font-medium px-2 py-1 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300">{course.level}</span>
                <span className="flex items-center text-xs font-medium px-2 py-1 rounded-full bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400">
                    <BarChart3 size={12} className="mr-1"/> Рейтинг: {course.rating_avg}
                </span>
            </div>
            <h2 className="text-3xl font-bold mt-2 text-gray-900 dark:text-white">{course.title}</h2>
            <p className="text-gray-500 dark:text-gray-400 mt-2 max-w-2xl">{course.description}</p>
          </div>
        </div>

        <div className="mt-8 space-y-3">
          <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-4">Программа курса</h3>
          {course.lectures.map((lecture, idx) => (
            <div key={lecture.id} className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden bg-gray-50 dark:bg-gray-800/50">
              
              <div 
                className="flex items-center p-4 cursor-pointer hover:bg-white dark:hover:bg-gray-700 transition-colors group"
                onClick={() => handleLectureSelect(lecture)}
              >
                {/* 1. Стрелочка слева (Кнопка раскрытия списка задач) */}
                <button 
                    onClick={(e) => toggleLectureExpand(lecture.id, e)}
                    className={`p-2 mr-3 rounded-full transition-all ${
                        expandedLectures[lecture.id] 
                        ? 'bg-indigo-100 dark:bg-indigo-900/50 text-indigo-600' 
                        : 'text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
                    }`}
                >
                    {expandedLectures[lecture.id] ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                </button>

                {/* Иконка типа контента */}
                <div className="bg-indigo-100 dark:bg-indigo-900/50 p-2 rounded-lg mr-4 text-indigo-600 dark:text-indigo-400 flex-shrink-0">
                  <BookOpen size={20} />
                </div>
                
                {/* Название и мета-информация */}
                <div className="flex-grow">
                   <h4 className="font-bold text-gray-900 dark:text-gray-100 text-lg group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                     {lecture.title}
                   </h4>
                   <div className="flex items-center mt-1 text-sm text-gray-500 dark:text-gray-400">
                       <span className="mr-4">{lecture.tasks?.length || 0} заданий</span>
                       {lecture.completed && (
                           <span className="text-green-500 flex items-center font-medium">
                               <CheckCircle size={14} className="mr-1"/> Пройдено
                           </span>
                       )}
                   </div>
                </div>
                
                {/* Play иконку УБРАЛИ */}
              </div>

              {/* Выпадающий список задач */}
              {expandedLectures[lecture.id] && lecture.tasks?.length > 0 && (
                  <div className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 p-2 pl-4 md:pl-20">
                      {lecture.tasks.map((task) => (
                          <div 
                            key={task.id} 
                            onClick={(e) => { e.stopPropagation(); handleTaskSelect(task); }} 
                            className="flex items-center p-3 mb-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700/50 cursor-pointer transition-colors"
                          >
                             <div className="mr-3 text-gray-400 min-w-[20px] text-center">
                                {task.type === 'numeric' && <Hash size={16} />}
                                {task.type === 'multiple-choice' && <CheckCircle size={16} />}
                                {task.type === 'open' && <FileText size={16} />}
                             </div>
                             <div className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate pr-4">
                                {/* Обрезаем текст вопроса, если длинный */}
                                {task.question.replace(/[*_#`]/g, '').substring(0, 80)}
                                {task.question.length > 80 ? '...' : ''}
                             </div>
                          </div>
                      ))}
                  </div>
              )}
              
              {/* Сообщение, если задач нет, но список раскрыли */}
              {expandedLectures[lecture.id] && (!lecture.tasks || lecture.tasks.length === 0) && (
                  <div className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 p-4 pl-20 text-sm text-gray-400 italic">
                      Нет заданий к этой теме.
                  </div>
              )}

            </div>
          ))}


        </div>
      </div>
    </div>
  );
};

export default CourseDetail;