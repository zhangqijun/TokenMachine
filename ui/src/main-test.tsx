import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <div style={{ padding: '20px', background: 'lightblue' }}>
      <h1>Test Page</h1>
      <p>If you can see this, React is working!</p>
    </div>
  </StrictMode>,
)
