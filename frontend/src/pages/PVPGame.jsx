import React, { useState, useEffect, useRef } from 'react';
import {
  Swords, Zap, Trophy, Loader2, Users, ArrowLeft, CheckCircle, XCircle,
  AlertTriangle, Clock, RefreshCw, BookOpen, SlidersHorizontal, DoorOpen
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const PVPGame = () => {
  const { user, token } = useAuth();
  
  // === СОСТОЯНИЯ ===
  const [gameState, setGameState] = useState('lobby');
  const [roomCode, setRoomCode] = useState(null);
  const [joinCode, setJoinCode] = useState('');
  const [isJoinMode, setIsJoinMode] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [wsError, setWsError] = useState(null);
  
  // Игровые состояния
  const [opponentSolved, setOpponentSolved] = useState(0);
  const [opponentAnswered, setOpponentAnswered] = useState(false);
  const [timer, setTimer] = useState(300); // По умолчанию 5 минут
  const [myScore, setMyScore] = useState(0);
  const [opponentScore, setOpponentScore] = useState(0);
  const [currentTask, setCurrentTask] = useState(null);
  const [taskNumber, setTaskNumber] = useState(1);
  const [totalTasks, setTotalTasks] = useState(5);
  const [gameResult, setGameResult] = useState(null);
  const [inputAnswer, setInputAnswer] = useState('');
  const [feedback, setFeedback] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [countdown, setCountdown] = useState(3);
  const [attemptsLeft, setAttemptsLeft] = useState(3);
  
  // Настройки комнаты
  const [selectedTopic, setSelectedTopic] = useState(null);
  const [taskCount, setTaskCount] = useState(5);
  const [matchDuration, setMatchDuration] = useState(300); // 5 минут = 300 сек
  const [topics, setTopics] = useState([]);
  const [maxAvailableTasks, setMaxAvailableTasks] = useState(10);
  const [isLoadingTopics, setIsLoadingTopics] = useState(true);
  const [isLoadingTaskCount, setIsLoadingTaskCount] = useState(false);
  
  const wsRef = useRef(null);
  const inputRef = useRef(null);

  // === ПОДКЛЮЧЕНИЕ WEBSOCKET ===
  useEffect(() => {
    if (!token) {
      setWsError("Ошибка авторизации: Нет токена");
      return;
    }
    
    const backendUrl = '127.0.0.1:8000';
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${backendUrl}/ws/pvp?token=${token}`;
    
    try {
      const socket = new WebSocket(wsUrl);
      socket.onopen = () => {
        console.log('✅ WS: Соединение установлено');
        setWsConnected(true);
        setWsError(null);
      };
      
      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleServerMessage(data);
        } catch (e) {
          console.error('❌ Ошибка парсинга сообщения:', e, event.data);
        }
      };
      
      socket.onclose = (event) => {
        console.log(`❌ WS: Закрыто (код ${event.code})`, event.reason || '');
        setWsConnected(false);
        if (![1000, 1001].includes(event.code)) {
          setWsError(`Соединение разорвано (код ${event.code})`);
        }
      };
      
      socket.onerror = (error) => {
        console.error('🔥 WS: Критическая ошибка', error);
        setWsError("Ошибка подключения к серверу");
      };
      
      wsRef.current = socket;
      return () => socket.close();
    } catch (e) {
      console.error("💥 Ошибка создания WebSocket:", e);
      setWsError("Не удалось инициализировать подключение");
    }
  }, [token]);

  // === ЗАГРУЗКА ТЕМ И КОЛИЧЕСТВА ЗАДАЧ ===
  useEffect(() => {
    const loadTopics = async () => {
      if (!token) return;
      try {
        setIsLoadingTopics(true);
        const res = await fetch('http://127.0.0.1:8000/api/v1/topics?limit=50', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setTopics(data.items || []);
        }
      } catch (e) {
        console.error('❌ Ошибка загрузки тем:', e);
      } finally {
        setIsLoadingTopics(false);
      }
    };
    loadTopics();
  }, [token]);

  useEffect(() => {
    const loadTaskCount = async () => {
      if (!token) return;
      try {
        setIsLoadingTaskCount(true);
        const url = selectedTopic?.id
          ? `http://127.0.0.1:8000/api/v1/tasks/count?topic_id=${selectedTopic.id}`
          : 'http://127.0.0.1:8000/api/v1/tasks/count';
        const res = await fetch(url, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          const available = Math.min(data.total || 10, 10);
          setMaxAvailableTasks(available);
          if (taskCount > available) setTaskCount(available);
        }
      } catch (e) {
        console.error('❌ Ошибка загрузки количества задач:', e);
        setMaxAvailableTasks(10);
        if (taskCount > 10) setTaskCount(10);
      } finally {
        setIsLoadingTaskCount(false);
      }
    };
    loadTaskCount();
  }, [selectedTopic, token]);

  // === ОБРАБОТКА СООБЩЕНИЙ ОТ СЕРВЕРА ===
  const handleServerMessage = (data) => {
    if (!user) return;
    
    switch (data.type) {
      case 'status':
        if (data.status === 'searching') setGameState('searching');
        if (data.status === 'idle') {
          setGameState('lobby');
          setRoomCode(null);
          setIsJoinMode(false);
        }
        break;
        
      case 'room_created':
        setGameState('room_lobby');
        setRoomCode(data.room_code);
        break;
        
      case 'countdown':
        setGameState('countdown');
        setCountdown(data.value);
        break;
        
      case 'game_start':
        setGameState('playing');
        setCurrentTask(data.current_task);
        setTotalTasks(data.total_tasks || 5);
        setTimer(data.timer || 300);
        setTaskNumber(1);
        setAttemptsLeft(data.attempts_left || 3);
        setMyScore(0);
        setOpponentScore(0);
        setOpponentAnswered(false);
        setFeedback(null);
        setInputAnswer('');
        setRoomCode(null);
        break;
        
      case 'next_task':
        setCurrentTask(data.current_task);
        setTaskNumber(prev => prev + 1);
        setAttemptsLeft(data.attempts_left || 3);
        setOpponentAnswered(false);
        setFeedback(null);
        setInputAnswer('');
        setIsSubmitting(false);
        break;
        
      case 'opponent_progress':
        setOpponentAnswered(data.opponent_answered);
        setOpponentScore(data.opponent_score);
        break;
        
      case 'match_update':
        setTimer(data.timer);
        setMyScore(data.scores?.[user.id] || 0);
        const oppId = Object.keys(data.scores || {}).find(id => parseInt(id) !== user.id);
        if (oppId) setOpponentScore(data.scores[oppId]);
        break;
        
      case 'answer_result':
        setFeedback(data.is_correct ? 'correct' : 'incorrect');
        if (!data.is_correct) {
          setAttemptsLeft(data.attempts_left || 0);
        }
        setTimeout(() => {
          if (!data.is_correct && (data.attempts_left || 0) <= 0) {
            alert(`Попытки исчерпаны. Правильный ответ: ${data.correct_answer}`);
          }
          setFeedback(null);
          setIsSubmitting(false);
        }, 1500);
        break;

      case 'attempts_exhausted':
        setFeedback('incorrect');
        setTimeout(() => setFeedback(null), 1500);
        setIsSubmitting(false);
        break;
        
      case 'game_finished':
        setGameState('finished');
        setGameResult({
          scores: data.scores,
          rating_changes: data.rating_changes,
          winner_id: data.winner_id,
          disconnected_player_id: data.disconnected_player_id
        });
        setTimeout(() => {
          setGameState('lobby');
          setGameResult(null);
        }, 10000);
        break;
        
      case 'game_cancelled':
        alert(`Матч отменён: ${data.reason}`);
        setGameState('lobby');
        break;
        
      case 'error':
        alert(`Ошибка: ${data.message}`);
        if (['searching', 'room_lobby', 'countdown', 'playing'].includes(gameState)) {
          setGameState('lobby');
        }
        setIsSubmitting(false);
        break;
        
      default:
        console.log('❓ Неизвестный тип сообщения:', data.type);
    }
  };

  // === ОТПРАВКА СООБЩЕНИЙ НА СЕРВЕР ===
  const send = (msg) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    } else {
      setWsError("Соединение разорвано. Перезагрузите страницу.");
    }
  };

  // === ДЕЙСТВИЯ ===
  const findMatch = () => {
    if (gameState !== 'lobby') return;
    send({ 
      action: 'find_match',
      topic_id: selectedTopic?.id || null,
      task_count: taskCount,
      match_duration: matchDuration
    });
  };

  const createRoom = () => {
    if (gameState !== 'lobby') return;
    if (taskCount < 1 || taskCount > maxAvailableTasks) {
      alert(`Количество задач должно быть от 1 до ${maxAvailableTasks}`);
      return;
    }
    if (matchDuration < 60 || matchDuration > 1800) {
      alert('Время матча должно быть от 60 до 1800 секунд (1-30 минут)');
      return;
    }
    send({
      action: 'create_room',
      topic_id: selectedTopic?.id || null,
      task_count: taskCount,
      match_duration: matchDuration
    });
  };

  const joinRoom = () => {
    if (joinCode.length !== 4 || gameState !== 'lobby') {
      alert("Код должен состоять из 4 цифр");
      return;
    }
    send({ action: 'join_room', code: joinCode });
  };

  const cancel = () => {
    send({ action: 'cancel_search' });
    setGameState('lobby');
    setRoomCode(null);
    setIsJoinMode(false);
  };

  const leaveGame = () => {
    if (gameState === 'playing' && wsRef.current?.readyState === WebSocket.OPEN) {
      if (window.confirm("Вы уверены, что хотите покинуть матч? Это будет засчитано как поражение.")) {
        send({ action: 'leave_game' });
        setGameState('lobby');
        setCurrentTask(null);
      }
    }
  };

  const submitAnswer = (e) => {
    e?.preventDefault();
    if (!inputAnswer.trim() || isSubmitting || gameState !== 'playing' || attemptsLeft <= 0) return;
    setIsSubmitting(true);
    send({ action: 'submit_answer', answer: inputAnswer.trim() });
    setInputAnswer('');
  };

  const handleOptionClick = (option) => {
    if (isSubmitting || gameState !== 'playing' || attemptsLeft <= 0) return;
    setIsSubmitting(true);
    send({ action: 'submit_answer', answer: option });
  };

  // === РЕНДЕР: ОШИБКА ПОДКЛЮЧЕНИЯ ===
  if (wsError) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 to-black flex flex-col items-center justify-center p-4 text-white">
        <AlertTriangle size={64} className="text-red-500 mb-4" />
        <h2 className="text-2xl font-bold mb-2">Ошибка подключения</h2>
        <p className="text-gray-400 mb-6 max-w-md text-center">{wsError}</p>
        <button
          onClick={() => window.location.reload()}
          className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 rounded-lg flex items-center gap-2 transition"
        >
          <RefreshCw size={18} /> Обновить страницу
        </button>
      </div>
    );
  }

  // === РЕНДЕР: ОБРАТНЫЙ ОТСЧЁТ ===
  if (gameState === 'countdown') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 to-black flex flex-col items-center justify-center p-4">
        <div className="text-9xl font-bold text-indigo-400 mb-6 animate-pulse">
          {countdown}
        </div>
        <div className="flex items-center gap-3 text-gray-400 text-lg">
          <Clock size={24} />
          <span>До начала игры...</span>
        </div>
      </div>
    );
  }

  // === РЕНДЕР: ИГРА В ПРОЦЕССЕ ===
  if (gameState === 'playing' && currentTask) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-900 to-black p-4 md:p-6">
        {/* Шапка с прогрессом */}
        <div className="flex flex-col md:flex-row justify-between items-center mb-6 pb-4 border-b border-gray-800 gap-4">
          <div className="text-left w-full md:w-auto">
            <div className="text-gray-500 text-sm">Вы</div>
            <div className="text-sm text-indigo-300 mb-1">Задача: {taskNumber}/{totalTasks}</div>
            <div className="text-3xl font-bold text-indigo-400">{myScore}</div>
          </div>
          
          <div className="text-center w-full md:w-auto">
            <div className="text-gray-500 text-sm">Время матча</div>
            <div className="flex items-center justify-center mt-1">
              <Clock size={24} className="text-amber-400 mr-2" />
              <span className={`text-2xl font-bold ${timer <= 10 ? 'text-red-500 animate-pulse' : 'text-white'}`}>
                {Math.floor(timer / 60)}:{(timer % 60).toString().padStart(2, '0')}
              </span>
            </div>
            {attemptsLeft > 0 && (
              <div className="text-xs text-amber-300 mt-1">
                Попыток на задачу: {attemptsLeft}
              </div>
            )}
          </div>
          
          <div className="text-right w-full md:w-auto">
            <div className="text-gray-500 text-sm">Соперник</div>
            <div className="text-sm text-rose-300 mb-1">
              {opponentAnswered ? '✅ Ответил' : '⏳ Решает'}
            </div>
            <div className="text-3xl font-bold text-rose-400">{opponentScore}</div>
          </div>
        </div>
        
        {/* Задача */}
        <div className="bg-gray-800 rounded-2xl p-6 md:p-8 mb-8 border border-gray-700 max-w-3xl mx-auto">
          <div className="text-lg text-gray-300 mb-4">
            <span className="font-bold text-indigo-300">Вопрос {taskNumber}:</span>
          </div>
          <div className="text-2xl font-bold text-white mb-6">{currentTask.question}</div>
          
          {/* Варианты ответов */}
          {currentTask.options && currentTask.options.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {currentTask.options.map((option, idx) => (
                <button
                  key={idx}
                  onClick={() => handleOptionClick(option)}
                  disabled={isSubmitting || feedback !== null || attemptsLeft <= 0}
                  className={`p-4 rounded-xl text-left font-medium transition-all ${
                    feedback === 'correct' && option === currentTask.correct_answer
                      ? 'bg-green-500/20 border-2 border-green-500 text-green-300'
                      : feedback === 'incorrect' && option === currentTask.correct_answer
                      ? 'bg-green-500/20 border-2 border-green-500 text-green-300'
                      : feedback === 'incorrect' && option === inputAnswer
                      ? 'bg-red-500/20 border-2 border-red-500 text-red-300'
                      : isSubmitting || feedback !== null || attemptsLeft <= 0
                      ? 'bg-gray-700 cursor-not-allowed opacity-70'
                      : 'bg-gray-700 hover:bg-gray-600 border border-gray-600'
                  }`}
                >
                  {option}
                </button>
              ))}
            </div>
          ) : (
            <form onSubmit={submitAnswer} className="space-y-4">
              <input
                ref={inputRef}
                type="text"
                value={inputAnswer}
                onChange={(e) => setInputAnswer(e.target.value)}
                disabled={isSubmitting || feedback !== null || attemptsLeft <= 0}
                placeholder={attemptsLeft <= 0 ? "Попытки исчерпаны" : "Введите ответ..."}
                className={`w-full p-4 bg-gray-700 border ${
                  feedback === 'correct'
                    ? 'border-green-500'
                    : feedback === 'incorrect'
                    ? 'border-red-500'
                    : 'border-gray-600'
                } rounded-xl text-white text-lg focus:outline-none focus:ring-2 focus:ring-indigo-500`}
                autoFocus
              />
              <button
                type="submit"
                disabled={isSubmitting || !inputAnswer.trim() || feedback !== null || attemptsLeft <= 0}
                className={`w-full py-3 rounded-xl font-bold text-lg transition ${
                  isSubmitting || !inputAnswer.trim() || feedback !== null || attemptsLeft <= 0
                    ? 'bg-gray-600 cursor-not-allowed'
                    : 'bg-indigo-600 hover:bg-indigo-700'
                }`}
              >
                {isSubmitting ? 'Проверка...' : 'Ответить'}
              </button>
            </form>
          )}
          
          {/* Фидбек */}
          {feedback && (
            <div className={`mt-6 p-4 rounded-xl flex items-center justify-center ${
              feedback === 'correct' ? 'bg-green-500/15 text-green-400' : 'bg-red-500/15 text-red-400'
            }`}>
              {feedback === 'correct' ? (
                <>
                  <CheckCircle size={28} className="mr-3" />
                  <span className="text-xl font-bold">Правильно! +1 очко</span>
                </>
              ) : (
                <>
                  <XCircle size={28} className="mr-3" />
                  <span className="text-xl font-bold">Неправильно</span>
                </>
              )}
            </div>
          )}
        </div>
        
        {/* Кнопка выхода из матча */}
        <div className="text-center">
          <button
            onClick={leaveGame}
            className="px-6 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium flex items-center gap-2 mx-auto transition"
          >
            <DoorOpen size={18} /> Покинуть матч (поражение)
          </button>
        </div>
      </div>
    );
  }

  // === РЕНДЕР: РЕЗУЛЬТАТ ИГРЫ ===
  if (gameState === 'finished' && gameResult) {
    const isWinner = gameResult.winner_id === user?.id;
    const isDraw = !gameResult.winner_id;
    const isForfeit = gameResult.disconnected_player_id !== undefined;
    const myChange = gameResult.rating_changes?.[user?.id] || 0;
    
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 to-black flex flex-col items-center justify-center p-4 animate-fadeIn">
        <div className={`p-8 rounded-full mb-6 ${
          isWinner ? 'bg-green-500/20 border-4 border-green-500' :
          isDraw ? 'bg-amber-500/20 border-4 border-amber-500' :
          'bg-red-500/20 border-4 border-red-500'
        }`}>
          {isForfeit ? (
            <DoorOpen size={64} className="text-gray-400" />
          ) : isWinner ? (
            <Trophy size={64} className="text-yellow-400" />
          ) : isDraw ? (
            <div className="text-5xl font-bold text-amber-400">=</div>
          ) : (
            <Swords size={64} className="text-gray-500" />
          )}
        </div>
        
        <h2 className="text-4xl font-bold text-white mb-2">
          {isForfeit ? (gameResult.disconnected_player_id === user?.id ? 'ПОРАЖЕНИЕ' : 'ПОБЕДА') : 
           isWinner ? 'ПОБЕДА!' : 
           isDraw ? 'НИЧЬЯ' : 'ПОРАЖЕНИЕ'}
        </h2>
        
        {isForfeit && (
          <p className="text-amber-400 mb-4">
            {gameResult.disconnected_player_id === user?.id 
              ? 'Вы покинули матч' 
              : 'Соперник покинул матч'}
          </p>
        )}
        
        <div className="flex items-baseline my-4">
          <span className="text-6xl font-bold text-indigo-400 mr-4">{gameResult.scores?.[user?.id] || 0}</span>
          <span className="text-4xl text-gray-500 mx-4">:</span>
          <span className="text-6xl font-bold text-rose-400 ml-4">
            {Object.values(gameResult.scores || {}).find((v, i) =>
              Object.keys(gameResult.scores || {})[i] !== String(user?.id)
            ) || 0}
          </span>
        </div>
        
        <div className="bg-gray-800 p-4 rounded-xl mb-6 max-w-md w-full text-center">
          <div className="flex justify-between text-lg mb-2">
            <span>Изменение рейтинга:</span>
            <span className={`font-bold ${
              myChange > 0 ? 'text-green-400' : myChange < 0 ? 'text-red-400' : 'text-gray-300'
            }`}>
              {myChange > 0 ? '+' : ''}{myChange}
            </span>
          </div>
        </div>
        
        <p className="text-gray-400 mb-8">Возврат в лобби через 10 секунд...</p>
        <button
          onClick={() => { setGameState('lobby'); setGameResult(null); }}
          className="px-8 py-3 bg-indigo-600 hover:bg-indigo-700 rounded-xl font-bold text-lg flex items-center gap-2"
        >
          <ArrowLeft size={20} /> Вернуться в лобби
        </button>
      </div>
    );
  }

  // === РЕНДЕР: ПОИСК / КОМНАТА ===
  if (gameState === 'searching' || gameState === 'room_lobby') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 to-black flex flex-col items-center justify-center p-4">
        <div className="relative mb-8">
          <div className="absolute inset-0 bg-indigo-500 rounded-full animate-ping opacity-25"></div>
          <Loader2 size={64} className="text-indigo-500 animate-spin relative z-10" />
        </div>
        {gameState === 'searching' ? (
          <>
            <h2 className="text-2xl font-bold text-white mb-2">Поиск соперника...</h2>
            <p className="text-gray-500 mb-8">Подбираем равного по силе противника</p>
          </>
        ) : (
          <>
            <h2 className="text-2xl font-bold text-white mb-2">Комната создана</h2>
            <div className="bg-gray-800 px-8 py-4 rounded-xl border border-indigo-500/50 mb-6 flex flex-col items-center">
              <span className="text-gray-400 text-sm mb-1">Код комнаты</span>
              <span className="text-4xl font-mono font-bold text-indigo-400 tracking-widest">{roomCode}</span>
            </div>
            <p className="text-gray-500 mb-8">Сообщите этот код другу</p>
          </>
        )}
        <button onClick={cancel} className="px-6 py-2 border border-gray-600 text-gray-300 rounded-lg hover:bg-gray-800 transition">
          Отмена
        </button>
      </div>
    );
  }

  // === РЕНДЕР: ЛОББИ ===
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-black flex flex-col items-center justify-center p-4 animate-fadeIn">
      <div className="bg-indigo-500/20 p-8 rounded-full mb-8 shadow-xl border border-indigo-500/30">
        <Swords size={80} className="text-indigo-400" />
      </div>
      <h1 className="text-5xl font-bold text-white mb-8 tracking-tight">PVP Arena</h1>
      
      {isJoinMode ? (
        // Режим присоединения к комнате
        <div className="bg-gray-800 p-8 rounded-2xl border border-gray-700 w-full max-w-sm">
          <h3 className="text-white text-xl font-bold mb-4 text-center">Введите код комнаты</h3>
          <input
            type="text"
            value={joinCode}
            onChange={(e) => setJoinCode(e.target.value.replace(/\D/g, '').slice(0, 4))}
            placeholder="1234"
            maxLength={4}
            className="w-full bg-gray-900 text-white text-center text-3xl tracking-widest py-3 rounded-lg border border-gray-600 focus:border-indigo-500 mb-6 outline-none"
          />
          <div className="flex gap-4">
            <button onClick={() => setIsJoinMode(false)} className="flex-1 py-3 bg-gray-700 text-gray-300 rounded-lg font-bold hover:bg-gray-600 transition">Отмена</button>
            <button onClick={joinRoom} className="flex-1 py-3 bg-indigo-600 text-white rounded-lg font-bold hover:bg-indigo-500 transition">Войти</button>
          </div>
        </div>
      ) : (
        // Основное лобби с настройками
        <div className="flex flex-col items-center w-full max-w-2xl">
          <div className="bg-gray-800 p-6 rounded-2xl border border-gray-700 w-full mb-6">
            <div className="flex items-center gap-2 mb-4">
              <SlidersHorizontal size={20} className="text-indigo-400" />
              <h3 className="text-white text-lg font-bold">Настройки игры</h3>
            </div>
            
            {/* Выбор темы */}
            <div className="mb-4">
              <label className="block text-gray-400 text-sm mb-2 flex items-center gap-1">
                <BookOpen size={14} /> Тема (опционально)
              </label>
              <select
                value={selectedTopic?.id || ''}
                onChange={(e) => {
                  const topic = topics.find(t => t.id === parseInt(e.target.value));
                  setSelectedTopic(topic || null);
                }}
                disabled={isLoadingTopics}
                className="w-full bg-gray-900 text-white p-3 rounded-lg border border-gray-600 focus:border-indigo-500 outline-none"
              >
                <option value="">Любая тема (рандом)</option>
                {topics.map(topic => (
                  <option key={topic.id} value={topic.id}>{topic.name}</option>
                ))}
              </select>
              {isLoadingTopics && (
                <div className="text-xs text-gray-500 mt-1 flex items-center gap-1">
                  <Loader2 size={14} className="animate-spin" /> Загрузка тем...
                </div>
              )}
            </div>
            
            {/* Количество задач */}
            <div className="mb-4">
              <label className="block text-gray-400 text-sm mb-2">
                Количество задач (макс. {maxAvailableTasks})
              </label>
              <input
                type="number"
                min="1"
                max={maxAvailableTasks}
                value={taskCount}
                onChange={(e) => {
                  const val = parseInt(e.target.value) || 1;
                  setTaskCount(Math.max(1, Math.min(val, maxAvailableTasks)));
                }}
                disabled={isLoadingTaskCount}
                className="w-full bg-gray-900 text-white p-3 rounded-lg border border-gray-600 focus:border-indigo-500 outline-none"
              />
              <p className="text-xs text-gray-500 mt-1">
                {selectedTopic
                  ? `Доступно ${maxAvailableTasks} задач по теме "${selectedTopic.name}"`
                  : `Доступно ${maxAvailableTasks} задач во всех темах`}
              </p>
            </div>
            
            {/* Время матча */}
            <div>
              <label className="block text-gray-400 text-sm mb-2">
                Время матча (секунд, 60-1800)
              </label>
              <input
                type="number"
                min="60"
                max="1800"
                value={matchDuration}
                onChange={(e) => {
                  const val = parseInt(e.target.value) || 60;
                  setMatchDuration(Math.max(60, Math.min(val, 1800)));
                }}
                className="w-full bg-gray-900 text-white p-3 rounded-lg border border-gray-600 focus:border-indigo-500 outline-none"
              />
              <p className="text-xs text-gray-500 mt-1">
                Текущее: {Math.floor(matchDuration / 60)} мин {matchDuration % 60} сек
              </p>
            </div>
          </div>
          
          {/* Кнопки действий */}
          <div className="flex flex-col gap-4 w-full max-w-sm">
            <button
              onClick={findMatch}
              className="flex items-center justify-center gap-3 px-8 py-4 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-2xl text-xl transition-all shadow-lg shadow-indigo-500/20"
            >
              <Zap className="fill-current" /> ИГРАТЬ НА РЕЙТИНГ
            </button>
            <div className="flex gap-4">
              <button
                onClick={createRoom}
                className="flex-1 py-4 bg-gray-800 hover:bg-gray-700 text-gray-300 font-bold rounded-xl border border-gray-700 transition-colors flex flex-col items-center"
              >
                <Users className="mb-1" /> Создать
              </button>
              <button
                onClick={() => setIsJoinMode(true)}
                className="flex-1 py-4 bg-gray-800 hover:bg-gray-700 text-gray-300 font-bold rounded-xl border border-gray-700 transition-colors flex flex-col items-center"
              >
                <ArrowLeft className="rotate-180 mb-1" /> Войти
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PVPGame;