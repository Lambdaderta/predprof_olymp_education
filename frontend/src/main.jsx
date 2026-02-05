import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

import 'katex/dist/katex.min.css'; 

// Добавляем класс dark по умолчанию для корректной работы темной темы
document.documentElement.classList.add('dark')

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)