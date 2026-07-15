import { Routes, Route, Navigate } from "react-router-dom";
import MainLayout from "./components/MainLayout";
import Dashboard from "./pages/Dashboard";
import Products from "./pages/Products";
import Monitor from "./pages/Monitor";
import Reports from "./pages/Reports";
import Config from "./pages/Config";

function App() {
  return (
    <Routes>
      <Route path="/" element={<MainLayout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="products" element={<Products />} />
        <Route path="monitor" element={<Monitor />} />
        <Route path="reports" element={<Reports />} />
        <Route path="config" element={<Config />} />
      </Route>
    </Routes>
  );
}

export default App;