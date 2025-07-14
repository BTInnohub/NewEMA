import React, { useState, useEffect, useContext, createContext } from 'react';
import axios from 'axios';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Auth Context
const AuthContext = createContext();

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchUser();
    }
  }, [token]);
  
  const fetchUser = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`);
      setUser(response.data);
    } catch (error) {
      console.error('Error fetching user:', error);
      logout();
    }
  };
  
  const login = async (email, password) => {
    try {
      const response = await axios.post(`${API}/auth/login`, { email, password });
      const { access_token, user } = response.data;
      setToken(access_token);
      setUser(user);
      localStorage.setItem('token', access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      return true;
    } catch (error) {
      console.error('Login error:', error);
      return false;
    }
  };
  
  const register = async (email, password, name, role = 'security') => {
    try {
      await axios.post(`${API}/auth/register`, { email, password, name, role });
      return await login(email, password);
    } catch (error) {
      console.error('Registration error:', error);
      return false;
    }
  };
  
  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
  };
  
  return (
    <AuthContext.Provider value={{ user, token, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// WebSocket Hook
const useWebSocket = () => {
  const [socket, setSocket] = useState(null);
  const [lastMessage, setLastMessage] = useState(null);
  
  useEffect(() => {
    const wsUrl = BACKEND_URL.replace('https://', 'wss://').replace('http://', 'ws://');
    const newSocket = new WebSocket(`${wsUrl}/ws`);
    
    newSocket.onopen = () => {
      console.log('WebSocket connected');
      setSocket(newSocket);
    };
    
    newSocket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      setLastMessage(message);
    };
    
    newSocket.onclose = () => {
      console.log('WebSocket disconnected');
      setSocket(null);
    };
    
    newSocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    return () => {
      newSocket.close();
    };
  }, []);
  
  return { socket, lastMessage };
};

// Login Component
const LoginForm = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({ email: '', password: '', name: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login, register } = useAuth();
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      let success;
      if (isLogin) {
        success = await login(formData.email, formData.password);
      } else {
        success = await register(formData.email, formData.password, formData.name);
      }
      
      if (!success) {
        setError(isLogin ? 'Invalid credentials' : 'Registration failed');
      }
    } catch (err) {
      setError('An error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="bg-white/10 backdrop-blur-md rounded-2xl p-8 shadow-2xl border border-white/20">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-white mb-2">EMA NextGen</h1>
            <p className="text-blue-200">Intrusion Detection System</p>
          </div>
          
          <form onSubmit={handleSubmit} className="space-y-6">
            {!isLogin && (
              <div>
                <label className="block text-sm font-medium text-gray-200 mb-2">Name</label>
                <input
                  type="text"
                  required
                  className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Enter your name"
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                />
              </div>
            )}
            
            <div>
              <label className="block text-sm font-medium text-gray-200 mb-2">Email</label>
              <input
                type="email"
                required
                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter your email"
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-200 mb-2">Password</label>
              <input
                type="password"
                required
                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter your password"
                value={formData.password}
                onChange={(e) => setFormData({...formData, password: e.target.value})}
              />
            </div>
            
            {error && (
              <div className="text-red-400 text-sm text-center">{error}</div>
            )}
            
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 text-white font-semibold rounded-lg transition-colors"
            >
              {loading ? 'Please wait...' : (isLogin ? 'Login' : 'Register')}
            </button>
          </form>
          
          <div className="mt-6 text-center">
            <button
              onClick={() => setIsLogin(!isLogin)}
              className="text-blue-300 hover:text-blue-200 text-sm"
            >
              {isLogin ? "Don't have an account? Register" : "Already have an account? Login"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Dashboard Components
const StatCard = ({ title, value, icon, color = "blue" }) => (
  <div className={`bg-gradient-to-br from-${color}-500 to-${color}-600 rounded-xl p-6 text-white`}>
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm opacity-90">{title}</p>
        <p className="text-3xl font-bold">{value}</p>
      </div>
      <div className="text-4xl opacity-80">{icon}</div>
    </div>
  </div>
);

const ZoneCard = ({ zone, onArm, onDisarm }) => {
  const getStatusColor = (status) => {
    switch (status) {
      case 'normal': return 'bg-green-500';
      case 'alarm': return 'bg-red-500 animate-pulse';
      case 'fault': return 'bg-yellow-500';
      default: return 'bg-gray-500';
    }
  };
  
  const getTypeIcon = (type) => {
    switch (type) {
      case 'motion': return '🚶';
      case 'door_contact': return '🚪';
      case 'glass_break': return '🪟';
      case 'fire': return '🔥';
      case 'burglary': return '🚨';
      default: return '⚠️';
    }
  };
  
  return (
    <div className="bg-white rounded-xl shadow-lg p-6 hover:shadow-xl transition-shadow">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{zone.name}</h3>
          <p className="text-sm text-gray-500">{zone.area}</p>
        </div>
        <div className="text-2xl">{getTypeIcon(zone.zone_type)}</div>
      </div>
      
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <div className={`w-3 h-3 rounded-full ${getStatusColor(zone.status)}`}></div>
          <span className="text-sm font-medium capitalize">{zone.status}</span>
        </div>
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${zone.is_armed ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800'}`}>
          {zone.is_armed ? 'Armed' : 'Disarmed'}
        </span>
      </div>
      
      <div className="flex space-x-2">
        {zone.is_armed ? (
          <button
            onClick={() => onDisarm(zone.id)}
            className="flex-1 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors"
          >
            Disarm
          </button>
        ) : (
          <button
            onClick={() => onArm(zone.id)}
            className="flex-1 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors"
          >
            Arm
          </button>
        )}
      </div>
    </div>
  );
};

const AlarmCard = ({ alarm, onAcknowledge, onResolve }) => {
  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'low': return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case 'medium': return 'bg-orange-100 text-orange-800 border-orange-300';
      case 'high': return 'bg-red-100 text-red-800 border-red-300';
      case 'critical': return 'bg-red-200 text-red-900 border-red-400';
      default: return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };
  
  return (
    <div className={`border-l-4 p-4 rounded-r-lg ${alarm.status === 'active' ? 'bg-red-50 border-red-500' : 'bg-gray-50 border-gray-300'}`}>
      <div className="flex items-start justify-between mb-2">
        <div>
          <h4 className="font-semibold text-gray-900">{alarm.zone_name}</h4>
          <p className="text-sm text-gray-600">{alarm.area}</p>
        </div>
        <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getSeverityColor(alarm.severity)}`}>
          {alarm.severity}
        </span>
      </div>
      
      <p className="text-sm text-gray-700 mb-3">{alarm.message}</p>
      
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-500">
          {new Date(alarm.triggered_at).toLocaleString()}
        </span>
        
        {alarm.status === 'active' && (
          <div className="flex space-x-2">
            <button
              onClick={() => onAcknowledge(alarm.id)}
              className="px-3 py-1 text-xs bg-yellow-600 hover:bg-yellow-700 text-white rounded transition-colors"
            >
              Acknowledge
            </button>
            <button
              onClick={() => onResolve(alarm.id)}
              className="px-3 py-1 text-xs bg-green-600 hover:bg-green-700 text-white rounded transition-colors"
            >
              Resolve
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

const Dashboard = () => {
  const [zones, setZones] = useState([]);
  const [alarms, setAlarms] = useState([]);
  const [stats, setStats] = useState({});
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(true);
  const { user, logout } = useAuth();
  const { lastMessage } = useWebSocket();
  
  useEffect(() => {
    fetchData();
  }, []);
  
  useEffect(() => {
    if (lastMessage) {
      handleWebSocketMessage(lastMessage);
    }
  }, [lastMessage]);
  
  const fetchData = async () => {
    try {
      const [zonesRes, alarmsRes, statsRes] = await Promise.all([
        axios.get(`${API}/zones`),
        axios.get(`${API}/alarms`),
        axios.get(`${API}/dashboard/stats`)
      ]);
      
      setZones(zonesRes.data);
      setAlarms(alarmsRes.data);
      setStats(statsRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const handleWebSocketMessage = (message) => {
    switch (message.type) {
      case 'alarm':
        setAlarms(prev => [message.data, ...prev]);
        break;
      case 'zone_update':
        setZones(prev => prev.map(zone => 
          zone.id === message.data.id ? { ...zone, ...message.data } : zone
        ));
        break;
      case 'alarm_update':
        setAlarms(prev => prev.map(alarm => 
          alarm.id === message.data.id ? { ...alarm, ...message.data } : alarm
        ));
        break;
      default:
        break;
    }
  };
  
  const handleArmZone = async (zoneId) => {
    try {
      await axios.post(`${API}/zones/${zoneId}/arm`);
      fetchData();
    } catch (error) {
      console.error('Error arming zone:', error);
    }
  };
  
  const handleDisarmZone = async (zoneId) => {
    try {
      await axios.post(`${API}/zones/${zoneId}/disarm`);
      fetchData();
    } catch (error) {
      console.error('Error disarming zone:', error);
    }
  };
  
  const handleAcknowledgeAlarm = async (alarmId) => {
    try {
      await axios.post(`${API}/alarms/${alarmId}/acknowledge`);
      fetchData();
    } catch (error) {
      console.error('Error acknowledging alarm:', error);
    }
  };
  
  const handleResolveAlarm = async (alarmId) => {
    try {
      await axios.post(`${API}/alarms/${alarmId}/resolve`);
      fetchData();
    } catch (error) {
      console.error('Error resolving alarm:', error);
    }
  };
  
  const createSampleZones = async () => {
    const sampleZones = [
      { name: 'Main Entrance', zone_type: 'door_contact', area: 'Building A' },
      { name: 'Lobby Motion', zone_type: 'motion', area: 'Building A' },
      { name: 'Server Room', zone_type: 'burglary', area: 'Building A' },
      { name: 'Emergency Exit', zone_type: 'door_contact', area: 'Building A' },
      { name: 'Reception Glass', zone_type: 'glass_break', area: 'Building A' },
      { name: 'Parking Lot', zone_type: 'motion', area: 'Exterior' }
    ];
    
    try {
      for (const zone of sampleZones) {
        await axios.post(`${API}/zones`, zone);
      }
      fetchData();
    } catch (error) {
      console.error('Error creating sample zones:', error);
    }
  };
  
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading system...</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-gray-900">EMA NextGen</h1>
              <span className="ml-2 text-sm text-gray-500">Intrusion Detection System</span>
            </div>
            
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">Welcome, {user?.name}</span>
              <button
                onClick={logout}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>
      
      {/* Navigation */}
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            {['overview', 'zones', 'alarms'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`py-4 px-1 border-b-2 font-medium text-sm capitalize ${
                  activeTab === tab
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>
      </nav>
      
      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'overview' && (
          <div className="space-y-8">
            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <StatCard title="Total Zones" value={stats.total_zones || 0} icon="🏢" color="blue" />
              <StatCard title="Active Alarms" value={stats.active_alarms || 0} icon="🚨" color="red" />
              <StatCard title="Armed Zones" value={stats.zones_armed || 0} icon="🔒" color="green" />
              <StatCard title="Events Today" value={stats.total_events_today || 0} icon="📊" color="purple" />
            </div>
            
            {/* Recent Alarms */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Recent Alarms</h2>
              <div className="space-y-4">
                {alarms.slice(0, 5).map((alarm) => (
                  <AlarmCard
                    key={alarm.id}
                    alarm={alarm}
                    onAcknowledge={handleAcknowledgeAlarm}
                    onResolve={handleResolveAlarm}
                  />
                ))}
                {alarms.length === 0 && (
                  <p className="text-gray-500 text-center py-8">No recent alarms</p>
                )}
              </div>
            </div>
          </div>
        )}
        
        {activeTab === 'zones' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-semibold text-gray-900">Security Zones</h2>
              {zones.length === 0 && (
                <button
                  onClick={createSampleZones}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
                >
                  Create Sample Zones
                </button>
              )}
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {zones.map((zone) => (
                <ZoneCard
                  key={zone.id}
                  zone={zone}
                  onArm={handleArmZone}
                  onDisarm={handleDisarmZone}
                />
              ))}
            </div>
            
            {zones.length === 0 && (
              <div className="text-center py-12">
                <p className="text-gray-500 mb-4">No security zones configured</p>
                <button
                  onClick={createSampleZones}
                  className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
                >
                  Create Sample Zones
                </button>
              </div>
            )}
          </div>
        )}
        
        {activeTab === 'alarms' && (
          <div className="space-y-6">
            <h2 className="text-2xl font-semibold text-gray-900">Alarm Management</h2>
            
            <div className="bg-white rounded-xl shadow-lg p-6">
              <div className="space-y-4">
                {alarms.map((alarm) => (
                  <AlarmCard
                    key={alarm.id}
                    alarm={alarm}
                    onAcknowledge={handleAcknowledgeAlarm}
                    onResolve={handleResolveAlarm}
                  />
                ))}
                {alarms.length === 0 && (
                  <div className="text-center py-12">
                    <p className="text-gray-500">No alarms to display</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

// Main App
const App = () => {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
};

const AppContent = () => {
  const { user } = useAuth();
  
  return (
    <div className="App">
      {user ? <Dashboard /> : <LoginForm />}
    </div>
  );
};

export default App;