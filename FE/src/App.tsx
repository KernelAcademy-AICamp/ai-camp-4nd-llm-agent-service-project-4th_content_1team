import { Route, Routes } from 'react-router-dom'
import './App.css'
import HomePage from './pages/HomePage'




function App() {
  return (
    <Routes>
      <Route>
        <Route index element={<HomePage />} />
      </Route>
    </Routes>
  )
}

export default App
