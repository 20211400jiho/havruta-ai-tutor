// index.jsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx' // Home 대신 App을 임포트

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App /> {/* App 컴포넌트 실행 */}
  </StrictMode>,
)