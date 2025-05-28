import React, { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link, useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend } from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';
import { 
  User, 
  LogOut, 
  Trophy, 
  Target, 
  Calendar, 
  MessageCircle, 
  ShoppingCart, 
  Activity, 
  Zap, 
  Users,
  Play,
  CheckCircle,
  Star,
  ChevronRight,
  Menu,
  X,
  Upload,
  TrendingUp,
  Award,
  Heart,
  Shield,
  Sparkles
} from 'lucide-react';
import axios from 'axios';
import toast, { Toaster } from 'react-hot-toast';
import io from 'socket.io-client';
import './App.css';

// Register Chart.js components
ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend);

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Auth Context
const AuthContext = createContext();

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchUser();
    } else {
      setLoading(false);
    }
  }, [token]);

  const fetchUser = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`);
      setUser(response.data);
    } catch (error) {
      console.error('Failed to fetch user:', error);
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    try {
      const response = await axios.post(`${API}/auth/login`, { email, password });
      const { access_token, user: userData } = response.data;
      
      setToken(access_token);
      setUser(userData);
      localStorage.setItem('token', access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      toast.success('Welcome back!');
      return true;
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Login failed');
      return false;
    }
  };

  const register = async (userData) => {
    try {
      const response = await axios.post(`${API}/auth/register`, userData);
      const { access_token, user: newUser } = response.data;
      
      setToken(access_token);
      setUser(newUser);
      localStorage.setItem('token', access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      toast.success('Welcome to Dominion!');
      return true;
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Registration failed');
      return false;
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
    toast.success('Logged out successfully');
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading }}>
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

// Header Component
const Header = () => {
  const { user, logout } = useAuth();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const location = useLocation();

  const navigation = [
    { name: 'Home', href: '/' },
    { name: 'Exercises', href: '/exercises' },
    { name: 'Progression', href: '/progression' },
    { name: 'Community', href: '/community' },
    { name: 'Shop', href: '/shop' },
    { name: 'Contact', href: '/contact' },
  ];

  return (
    <motion.header 
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      className="fixed top-0 w-full bg-black/90 backdrop-blur-md z-50 border-b border-gray-800"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center">
            <Link to="/" className="text-2xl font-bold text-white">
              <span className="bg-gradient-to-r from-blue-400 to-purple-600 bg-clip-text text-transparent">
                Dominion
              </span>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex space-x-8">
            {navigation.map((item) => (
              <Link
                key={item.name}
                to={item.href}
                className={`text-sm font-medium transition-colors ${
                  location.pathname === item.href
                    ? 'text-blue-400'
                    : 'text-gray-300 hover:text-white'
                }`}
              >
                {item.name}
              </Link>
            ))}
          </nav>

          {/* User Menu */}
          <div className="flex items-center space-x-4">
            {user ? (
              <div className="flex items-center space-x-4">
                <Link to="/profile" className="flex items-center space-x-2 text-gray-300 hover:text-white">
                  <User size={20} />
                  <span className="hidden sm:block">{user.username}</span>
                </Link>
                <button
                  onClick={logout}
                  className="flex items-center space-x-2 text-gray-300 hover:text-white"
                >
                  <LogOut size={20} />
                </button>
              </div>
            ) : (
              <div className="flex items-center space-x-4">
                <Link to="/login" className="text-gray-300 hover:text-white">Login</Link>
                <Link to="/register" className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg">
                  Sign Up
                </Link>
              </div>
            )}
          </div>

          {/* Mobile menu button */}
          <button
            className="md:hidden text-gray-300 hover:text-white"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
          >
            {isMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>
      </div>

      {/* Mobile Navigation */}
      <AnimatePresence>
        {isMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden bg-black/95 border-t border-gray-800"
          >
            <div className="px-4 py-4 space-y-4">
              {navigation.map((item) => (
                <Link
                  key={item.name}
                  to={item.href}
                  className="block text-gray-300 hover:text-white"
                  onClick={() => setIsMenuOpen(false)}
                >
                  {item.name}
                </Link>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.header>
  );
};

// Hero Section Component
const HeroSection = () => {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Background Image */}
      <div 
        className="absolute inset-0 bg-cover bg-center bg-no-repeat"
        style={{
          backgroundImage: `linear-gradient(rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0.5)), url('https://images.unsplash.com/photo-1526506118085-60ce8714f8c5')`
        }}
      />
      
      {/* Content */}
      <div className="relative z-10 text-center px-4 max-w-4xl mx-auto">
        <motion.h1
          initial={{ opacity: 0, y: 50 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="text-5xl md:text-7xl font-bold text-white mb-6"
        >
          Master Your
          <span className="bg-gradient-to-r from-blue-400 to-purple-600 bg-clip-text text-transparent block">
            Bodyweight Journey
          </span>
        </motion.h1>
        
        <motion.p
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="text-xl md:text-2xl text-gray-300 mb-8 leading-relaxed"
        >
          Progress through skill-based calisthenics exercises. Track your journey from beginner to elite levels with our comprehensive progression system.
        </motion.p>
        
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.4 }}
          className="flex flex-col sm:flex-row gap-4 justify-center"
        >
          <Link
            to="/exercises"
            className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-4 rounded-xl font-semibold transition-all transform hover:scale-105 flex items-center justify-center"
          >
            <Play className="mr-2" size={20} />
            Start Training
          </Link>
          <Link
            to="/progression"
            className="border border-gray-600 hover:border-gray-400 text-white px-8 py-4 rounded-xl font-semibold transition-all transform hover:scale-105 flex items-center justify-center"
          >
            <Target className="mr-2" size={20} />
            View Progressions
          </Link>
        </motion.div>
      </div>
      
      {/* Scroll Indicator */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1 }}
        className="absolute bottom-8 left-1/2 transform -translate-x-1/2"
      >
        <div className="w-6 h-10 border-2 border-gray-400 rounded-full flex justify-center">
          <motion.div
            animate={{ y: [0, 12, 0] }}
            transition={{ duration: 1.5, repeat: Infinity }}
            className="w-1 h-3 bg-gray-400 rounded-full mt-2"
          />
        </div>
      </motion.div>
    </section>
  );
};

// Features Section
const FeaturesSection = () => {
  const features = [
    {
      icon: <Target className="w-8 h-8" />,
      title: "Skill-Based Progression",
      description: "Master bodyweight exercises through systematic progression trees",
      image: "https://images.unsplash.com/photo-1634225251578-d5f6ffced78a"
    },
    {
      icon: <TrendingUp className="w-8 h-8" />,
      title: "Track Your Progress",
      description: "Visualize your journey with detailed analytics and charts",
      image: "https://images.pexels.com/photos/4775195/pexels-photo-4775195.jpeg"
    },
    {
      icon: <Users className="w-8 h-8" />,
      title: "Join the Community",
      description: "Connect with fellow athletes and share your achievements",
      image: "https://images.pexels.com/photos/8520627/pexels-photo-8520627.jpeg"
    },
    {
      icon: <Award className="w-8 h-8" />,
      title: "Earn Achievements",
      description: "Unlock badges and climb the leaderboard as you progress",
      image: "https://images.pexels.com/photos/2294361/pexels-photo-2294361.jpeg"
    }
  ];

  return (
    <section className="py-20 bg-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">
            Everything You Need to
            <span className="bg-gradient-to-r from-blue-400 to-purple-600 bg-clip-text text-transparent block">
              Master Calisthenics
            </span>
          </h2>
          <p className="text-xl text-gray-400 max-w-3xl mx-auto">
            Our comprehensive platform provides all the tools and guidance you need for your bodyweight fitness journey.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {features.map((feature, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 50 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: index * 0.1 }}
              className="bg-gray-800 rounded-xl p-6 text-center group hover:bg-gray-750 transition-all"
            >
              <div 
                className="w-full h-48 bg-cover bg-center rounded-lg mb-6"
                style={{ backgroundImage: `url(${feature.image})` }}
              />
              <div className="text-blue-400 mb-4 flex justify-center">
                {feature.icon}
              </div>
              <h3 className="text-xl font-bold text-white mb-3">{feature.title}</h3>
              <p className="text-gray-400">{feature.description}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};

// Home Page
const HomePage = () => {
  return (
    <div className="bg-black text-white">
      <HeroSection />
      <FeaturesSection />
      
      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-r from-blue-600 to-purple-600">
        <div className="max-w-4xl mx-auto text-center px-4">
          <motion.h2
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            className="text-4xl md:text-5xl font-bold mb-6"
          >
            Ready to Begin Your Journey?
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-xl mb-8 opacity-90"
          >
            Join thousands of athletes mastering bodyweight fitness with our proven progression system.
          </motion.p>
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <Link
              to="/register"
              className="bg-white text-blue-600 px-8 py-4 rounded-xl font-bold text-lg hover:bg-gray-100 transition-all transform hover:scale-105 inline-flex items-center"
            >
              <Sparkles className="mr-2" size={24} />
              Start Free Today
            </Link>
          </motion.div>
        </div>
      </section>
    </div>
  );
};

// Login Page
const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    const success = await login(email, password);
    if (success) {
      navigate('/');
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center px-4">
      <motion.div
        initial={{ opacity: 0, y: 50 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-md w-full space-y-8"
      >
        <div className="text-center">
          <h2 className="text-3xl font-bold text-white">Welcome Back</h2>
          <p className="mt-2 text-gray-400">Sign in to continue your fitness journey</p>
        </div>
        
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div>
            <label className="text-gray-300">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full mt-2 p-3 bg-gray-800 text-white rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none"
              required
            />
          </div>
          
          <div>
            <label className="text-gray-300">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full mt-2 p-3 bg-gray-800 text-white rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none"
              required
            />
          </div>
          
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-lg font-semibold transition-colors disabled:opacity-50"
          >
            {loading ? 'Signing In...' : 'Sign In'}
          </button>
        </form>
        
        <p className="text-center text-gray-400">
          Don't have an account?{' '}
          <Link to="/register" className="text-blue-400 hover:text-blue-300">
            Sign up
          </Link>
        </p>
      </motion.div>
    </div>
  );
};

// Register Page
const RegisterPage = () => {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    full_name: '',
    age: '',
    height: '',
    weight: '',
    university: '',
    city: ''
  });
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    const userData = {
      ...formData,
      age: formData.age ? parseInt(formData.age) : null,
      height: formData.height ? parseFloat(formData.height) : null,
      weight: formData.weight ? parseFloat(formData.weight) : null,
    };
    
    const success = await register(userData);
    if (success) {
      navigate('/');
    }
    setLoading(false);
  };

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center px-4 py-20">
      <motion.div
        initial={{ opacity: 0, y: 50 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-2xl w-full space-y-8"
      >
        <div className="text-center">
          <h2 className="text-3xl font-bold text-white">Join Dominion</h2>
          <p className="mt-2 text-gray-400">Start your bodyweight fitness journey today</p>
        </div>
        
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="text-gray-300">Username *</label>
              <input
                type="text"
                name="username"
                value={formData.username}
                onChange={handleChange}
                className="w-full mt-2 p-3 bg-gray-800 text-white rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none"
                required
              />
            </div>
            
            <div>
              <label className="text-gray-300">Full Name *</label>
              <input
                type="text"
                name="full_name"
                value={formData.full_name}
                onChange={handleChange}
                className="w-full mt-2 p-3 bg-gray-800 text-white rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none"
                required
              />
            </div>
            
            <div>
              <label className="text-gray-300">Email *</label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                className="w-full mt-2 p-3 bg-gray-800 text-white rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none"
                required
              />
            </div>
            
            <div>
              <label className="text-gray-300">Password *</label>
              <input
                type="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                className="w-full mt-2 p-3 bg-gray-800 text-white rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none"
                required
              />
            </div>
            
            <div>
              <label className="text-gray-300">Age</label>
              <input
                type="number"
                name="age"
                value={formData.age}
                onChange={handleChange}
                className="w-full mt-2 p-3 bg-gray-800 text-white rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none"
              />
            </div>
            
            <div>
              <label className="text-gray-300">Height (cm)</label>
              <input
                type="number"
                name="height"
                value={formData.height}
                onChange={handleChange}
                className="w-full mt-2 p-3 bg-gray-800 text-white rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none"
              />
            </div>
            
            <div>
              <label className="text-gray-300">Weight (kg)</label>
              <input
                type="number"
                name="weight"
                value={formData.weight}
                onChange={handleChange}
                className="w-full mt-2 p-3 bg-gray-800 text-white rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none"
              />
            </div>
            
            <div>
              <label className="text-gray-300">University</label>
              <input
                type="text"
                name="university"
                value={formData.university}
                onChange={handleChange}
                className="w-full mt-2 p-3 bg-gray-800 text-white rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none"
              />
            </div>
            
            <div className="md:col-span-2">
              <label className="text-gray-300">City</label>
              <input
                type="text"
                name="city"
                value={formData.city}
                onChange={handleChange}
                className="w-full mt-2 p-3 bg-gray-800 text-white rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>
          
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-lg font-semibold transition-colors disabled:opacity-50"
          >
            {loading ? 'Creating Account...' : 'Create Account'}
          </button>
        </form>
        
        <p className="text-center text-gray-400">
          Already have an account?{' '}
          <Link to="/login" className="text-blue-400 hover:text-blue-300">
            Sign in
          </Link>
        </p>
      </motion.div>
    </div>
  );
};

// Exercises Page
const ExercisesPage = () => {
  const [exercises, setExercises] = useState([]);
  const [pillars, setPillars] = useState([]);
  const [selectedPillar, setSelectedPillar] = useState('');
  const [selectedLevel, setSelectedLevel] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchExercises();
    fetchPillars();
  }, [selectedPillar, selectedLevel]);

  const fetchExercises = async () => {
    try {
      const params = new URLSearchParams();
      if (selectedPillar) params.append('pillar', selectedPillar);
      if (selectedLevel) params.append('skill_level', selectedLevel);
      
      const response = await axios.get(`${API}/exercises?${params}`);
      setExercises(response.data);
    } catch (error) {
      console.error('Failed to fetch exercises:', error);
      toast.error('Failed to load exercises');
    } finally {
      setLoading(false);
    }
  };

  const fetchPillars = async () => {
    try {
      const response = await axios.get(`${API}/exercises/pillars`);
      setPillars(response.data.pillars);
    } catch (error) {
      console.error('Failed to fetch pillars:', error);
    }
  };

  const getSkillLevelColor = (level) => {
    const colors = {
      'Beginner': 'bg-green-500',
      'Intermediate': 'bg-blue-500',
      'Advanced': 'bg-yellow-500',
      'Elite': 'bg-purple-500'
    };
    return colors[level] || 'bg-gray-500';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-white text-xl">Loading exercises...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 pt-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">
            Exercise Library
          </h1>
          <p className="text-xl text-gray-400 max-w-3xl mx-auto">
            Master bodyweight exercises through our comprehensive progression system.
          </p>
        </motion.div>

        {/* Filters */}
        <div className="flex flex-wrap gap-4 mb-8">
          <select
            value={selectedPillar}
            onChange={(e) => setSelectedPillar(e.target.value)}
            className="bg-gray-800 text-white px-4 py-2 rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none"
          >
            <option value="">All Pillars</option>
            {pillars.map((pillar) => (
              <option key={pillar} value={pillar}>{pillar}</option>
            ))}
          </select>

          <select
            value={selectedLevel}
            onChange={(e) => setSelectedLevel(e.target.value)}
            className="bg-gray-800 text-white px-4 py-2 rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none"
          >
            <option value="">All Levels</option>
            <option value="Beginner">Beginner</option>
            <option value="Intermediate">Intermediate</option>
            <option value="Advanced">Advanced</option>
            <option value="Elite">Elite</option>
          </select>
        </div>

        {/* Exercise Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {exercises.map((exercise) => (
            <motion.div
              key={exercise.id}
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-gray-800 rounded-xl p-6 hover:bg-gray-750 transition-all cursor-pointer"
              onClick={() => window.location.href = `/exercises/${exercise.id}`}
            >
              <div className="flex items-center justify-between mb-4">
                <span className={`px-3 py-1 rounded-full text-xs font-semibold text-white ${getSkillLevelColor(exercise.skill_level)}`}>
                  {exercise.skill_level}
                </span>
                <span className="text-xs text-gray-400">{exercise.pillar}</span>
              </div>
              
              <h3 className="text-xl font-bold text-white mb-3">{exercise.name}</h3>
              <p className="text-gray-400 mb-4 line-clamp-3">{exercise.description}</p>
              
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">#{exercise.progression_order}</span>
                <ChevronRight className="text-gray-400" size={20} />
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Exercise Detail Page
const ExerciseDetailPage = ({ exerciseId }) => {
  const [exercise, setExercise] = useState(null);
  const [progress, setProgress] = useState([]);
  const [logData, setLogData] = useState({ reps: '', sets: '', notes: '' });
  const [loading, setLoading] = useState(true);
  const [unlockedDate] = useState(new Date().toLocaleDateString());
  const { user } = useAuth();

  useEffect(() => {
    fetchExercise();
    if (user) {
      fetchProgress();
    }
  }, [exerciseId, user]);

  const fetchExercise = async () => {
    try {
      const response = await axios.get(`${API}/exercises/${exerciseId}`);
      setExercise(response.data);
    } catch (error) {
      console.error('Failed to fetch exercise:', error);
      toast.error('Exercise not found');
    } finally {
      setLoading(false);
    }
  };

  const fetchProgress = async () => {
    try {
      const response = await axios.get(`${API}/progress/${exerciseId}`);
      setProgress(response.data);
    } catch (error) {
      console.error('Failed to fetch progress:', error);
    }
  };

  const logProgress = async (e) => {
    e.preventDefault();
    if (!user) {
      toast.error('Please login to log progress');
      return;
    }

    try {
      await axios.post(`${API}/progress`, {
        exercise_id: exerciseId,
        reps: parseInt(logData.reps) || null,
        sets: parseInt(logData.sets) || null,
        notes: logData.notes || null
      });
      
      toast.success('Progress logged successfully!');
      setLogData({ reps: '', sets: '', notes: '' });
      fetchProgress();
    } catch (error) {
      console.error('Failed to log progress:', error);
      toast.error('Failed to log progress');
    }
  };

  const getNextExercise = () => {
    const nextOrder = exercise.progression_order + 1;
    return `Next: ${exercise.pillar} Level ${nextOrder}`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-white text-xl">Loading exercise...</div>
      </div>
    );
  }

  if (!exercise) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-white text-xl">Exercise not found</div>
      </div>
    );
  }

  const chartData = {
    labels: progress.map(p => new Date(p.date).toLocaleDateString()),
    datasets: [
      {
        label: 'Reps',
        data: progress.map(p => p.reps || 0),
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.5)',
      }
    ]
  };

  return (
    <div className="min-h-screen bg-gray-900 pt-20">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex items-center gap-4 mb-4">
            <span className={`px-3 py-1 rounded-full text-xs font-semibold text-white ${
              exercise.skill_level === 'Beginner' ? 'bg-green-500' :
              exercise.skill_level === 'Intermediate' ? 'bg-blue-500' :
              exercise.skill_level === 'Advanced' ? 'bg-yellow-500' : 'bg-purple-500'
            }`}>
              {exercise.skill_level}
            </span>
            <span className="text-gray-400">{exercise.pillar}</span>
            <span className="text-gray-500">#{exercise.progression_order}</span>
          </div>
          
          <h1 className="text-4xl font-bold text-white mb-4">{exercise.name}</h1>
          <p className="text-xl text-gray-400 mb-6">{exercise.description}</p>

          {/* Unlocked Status */}
          <div className="flex items-center gap-6 mb-6">
            <div className="flex items-center text-green-400">
              <CheckCircle className="mr-2" size={20} />
              <span>Unlocked on {unlockedDate}</span>
            </div>
            <div className="flex items-center text-blue-400">
              <Target className="mr-2" size={20} />
              <span>{getNextExercise()}</span>
            </div>
          </div>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - Instructions and Mistakes */}
          <div className="lg:col-span-2 space-y-8">
            {/* Demo Video Section */}
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              animate={{ opacity: 1, x: 0 }}
              className="bg-gray-800 rounded-xl p-6"
            >
              <h2 className="text-2xl font-bold text-white mb-4 flex items-center">
                <Play className="mr-3 text-blue-400" size={24} />
                Demo Video
              </h2>
              <div className="bg-gray-700 rounded-lg p-8 text-center">
                <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Play className="text-white" size={32} />
                </div>
                <p className="text-gray-400">Video tutorial coming soon!</p>
                <p className="text-sm text-gray-500 mt-2">Watch proper form and technique</p>
              </div>
            </motion.div>

            {/* Instructions */}
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              animate={{ opacity: 1, x: 0 }}
              className="bg-gray-800 rounded-xl p-6"
            >
              <h2 className="text-2xl font-bold text-white mb-4">How to Perform</h2>
              <ol className="space-y-3">
                {exercise.instructions.map((instruction, index) => (
                  <li key={index} className="flex items-start">
                    <span className="bg-blue-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold mr-3 mt-0.5">
                      {index + 1}
                    </span>
                    <span className="text-gray-300">{instruction}</span>
                  </li>
                ))}
              </ol>
            </motion.div>

            {/* Common Mistakes */}
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              animate={{ opacity: 1, x: 0 }}
              className="bg-gray-800 rounded-xl p-6"
            >
              <h2 className="text-2xl font-bold text-white mb-4">Common Mistakes</h2>
              <ul className="space-y-3">
                {exercise.common_mistakes.map((mistake, index) => (
                  <li key={index} className="flex items-start">
                    <X className="text-red-500 mr-3 mt-0.5" size={20} />
                    <span className="text-gray-300">{mistake}</span>
                  </li>
                ))}
              </ul>
            </motion.div>
          </div>

          {/* Right Column - Progress Tracking */}
          <div className="space-y-8">
            {/* Progression Status */}
            <motion.div
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              className="bg-gray-800 rounded-xl p-6"
            >
              <h3 className="text-xl font-bold text-white mb-4">Progression Status</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Current Level</span>
                  <span className={`font-semibold ${
                    exercise.skill_level === 'Beginner' ? 'text-green-400' :
                    exercise.skill_level === 'Intermediate' ? 'text-blue-400' :
                    exercise.skill_level === 'Advanced' ? 'text-yellow-400' : 'text-purple-400'
                  }`}>
                    {exercise.skill_level}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Progression #</span>
                  <span className="text-white font-semibold">{exercise.progression_order}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Times Logged</span>
                  <span className="text-white font-semibold">{progress.length}</span>
                </div>
              </div>
            </motion.div>

            {/* Progress Chart */}
            {user && progress.length > 0 && (
              <motion.div
                initial={{ opacity: 0, x: 30 }}
                animate={{ opacity: 1, x: 0 }}
                className="bg-gray-800 rounded-xl p-6"
              >
                <h3 className="text-xl font-bold text-white mb-4">Progress Chart</h3>
                <div className="bg-gray-700 p-4 rounded-lg">
                  <Line data={chartData} options={{ 
                    responsive: true, 
                    scales: { 
                      y: { beginAtZero: true, grid: { color: '#374151' } },
                      x: { grid: { color: '#374151' } }
                    },
                    plugins: {
                      legend: { labels: { color: '#d1d5db' } }
                    }
                  }} />
                </div>
              </motion.div>
            )}

            {/* Log Progress */}
            {user && (
              <motion.div
                initial={{ opacity: 0, x: 30 }}
                animate={{ opacity: 1, x: 0 }}
                className="bg-gray-800 rounded-xl p-6"
              >
                <h3 className="text-xl font-bold text-white mb-4">Log Progress</h3>
                <form onSubmit={logProgress} className="space-y-4">
                  <div>
                    <label className="text-gray-300">Reps</label>
                    <input
                      type="number"
                      value={logData.reps}
                      onChange={(e) => setLogData({ ...logData, reps: e.target.value })}
                      className="w-full mt-2 p-3 bg-gray-700 text-white rounded-lg border border-gray-600 focus:border-blue-500 focus:outline-none"
                    />
                  </div>
                  
                  <div>
                    <label className="text-gray-300">Sets</label>
                    <input
                      type="number"
                      value={logData.sets}
                      onChange={(e) => setLogData({ ...logData, sets: e.target.value })}
                      className="w-full mt-2 p-3 bg-gray-700 text-white rounded-lg border border-gray-600 focus:border-blue-500 focus:outline-none"
                    />
                  </div>
                  
                  <div>
                    <label className="text-gray-300">Notes</label>
                    <textarea
                      value={logData.notes}
                      onChange={(e) => setLogData({ ...logData, notes: e.target.value })}
                      className="w-full mt-2 p-3 bg-gray-700 text-white rounded-lg border border-gray-600 focus:border-blue-500 focus:outline-none"
                      rows={3}
                      placeholder="How did it feel?"
                    />
                  </div>
                  
                  <button
                    type="submit"
                    className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-lg font-semibold transition-colors flex items-center justify-center"
                  >
                    <TrendingUp className="mr-2" size={20} />
                    Log Progress
                  </button>
                </form>
              </motion.div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// Progression Page
const ProgressionPage = () => {
  const [exercises, setExercises] = useState([]);
  const [selectedPillar, setSelectedPillar] = useState('Horizontal Pull');
  const [pillars, setPillars] = useState([]);

  useEffect(() => {
    fetchPillars();
  }, []);

  useEffect(() => {
    if (selectedPillar) {
      fetchExercises();
    }
  }, [selectedPillar]);

  const fetchPillars = async () => {
    try {
      const response = await axios.get(`${API}/exercises/pillars`);
      setPillars(response.data.pillars);
      if (response.data.pillars.length > 0 && !selectedPillar) {
        setSelectedPillar(response.data.pillars[0]);
      }
    } catch (error) {
      console.error('Failed to fetch pillars:', error);
    }
  };

  const fetchExercises = async () => {
    try {
      const response = await axios.get(`${API}/exercises?pillar=${selectedPillar}`);
      setExercises(response.data);
    } catch (error) {
      console.error('Failed to fetch exercises:', error);
    }
  };

  const getSkillLevelColor = (level) => {
    const colors = {
      'Beginner': 'bg-green-500',
      'Intermediate': 'bg-blue-500',
      'Advanced': 'bg-yellow-500',
      'Elite': 'bg-purple-500'
    };
    return colors[level] || 'bg-gray-500';
  };

  return (
    <div className="min-h-screen bg-gray-900 pt-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">
            Skill Progression Trees
          </h1>
          <p className="text-xl text-gray-400 max-w-3xl mx-auto">
            Follow structured progression paths from beginner to elite levels in each movement pillar.
          </p>
        </motion.div>

        {/* Pillar Selector */}
        <div className="flex flex-wrap justify-center gap-4 mb-12">
          {pillars.map((pillar) => (
            <button
              key={pillar}
              onClick={() => setSelectedPillar(pillar)}
              className={`px-6 py-3 rounded-xl font-semibold transition-all ${
                selectedPillar === pillar
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              {pillar}
            </button>
          ))}
        </div>

        {/* Progression Tree */}
        <div className="relative">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {exercises.map((exercise, index) => (
              <motion.div
                key={exercise.id}
                initial={{ opacity: 0, y: 50 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="relative"
              >
                {/* Connection Line */}
                {index < exercises.length - 1 && (
                  <div className="hidden lg:block absolute top-1/2 -right-3 w-6 h-0.5 bg-gray-600 z-0" />
                )}
                
                <div className={`bg-gray-800 rounded-xl p-6 hover:bg-gray-750 transition-all cursor-pointer relative z-10 border-l-4 ${
                  exercise.skill_level === 'Beginner' ? 'border-green-500' :
                  exercise.skill_level === 'Intermediate' ? 'border-blue-500' :
                  exercise.skill_level === 'Advanced' ? 'border-yellow-500' : 'border-purple-500'
                }`}>
                  <div className="flex items-center justify-between mb-4">
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold text-white ${getSkillLevelColor(exercise.skill_level)}`}>
                      {exercise.skill_level}
                    </span>
                    <span className="text-xs text-gray-400">#{exercise.progression_order}</span>
                  </div>
                  
                  <h3 className="text-lg font-bold text-white mb-3">{exercise.name}</h3>
                  <p className="text-gray-400 text-sm mb-4 line-clamp-3">{exercise.description}</p>
                  
                  <Link
                    to={`/exercises/${exercise.id}`}
                    className="inline-flex items-center text-blue-400 hover:text-blue-300 transition-colors"
                  >
                    View Details
                    <ChevronRight size={16} className="ml-1" />
                  </Link>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

// Shop Page
const ShopPage = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProducts();
  }, []);

  const fetchProducts = async () => {
    try {
      const response = await axios.get(`${API}/products`);
      setProducts(response.data);
    } catch (error) {
      console.error('Failed to fetch products:', error);
      toast.error('Failed to load products');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-white text-xl">Loading products...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 pt-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">
            Fitness Equipment Shop
          </h1>
          <p className="text-xl text-gray-400 max-w-3xl mx-auto">
            High-quality equipment to enhance your bodyweight training journey.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {products.map((product) => (
            <motion.div
              key={product.id}
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-gray-800 rounded-xl overflow-hidden hover:bg-gray-750 transition-all"
            >
              <div className="h-48 bg-gray-700 flex items-center justify-center">
                <ShoppingCart className="text-gray-500" size={48} />
              </div>
              
              <div className="p-6">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-blue-400 font-semibold">{product.category}</span>
                  <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                    product.in_stock ? 'bg-green-500 text-white' : 'bg-red-500 text-white'
                  }`}>
                    {product.in_stock ? 'In Stock' : 'Out of Stock'}
                  </span>
                </div>
                
                <h3 className="text-xl font-bold text-white mb-3">{product.name}</h3>
                <p className="text-gray-400 mb-4">{product.description}</p>
                
                <div className="flex items-center justify-between">
                  <span className="text-2xl font-bold text-white">${product.price}</span>
                  <button 
                    className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    disabled={!product.in_stock}
                    onClick={() => toast.success('Contact form would open here!')}
                  >
                    {product.in_stock ? 'Contact to Buy' : 'Unavailable'}
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Community Page
const CommunityPage = () => {
  const [communities, setCommunities] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCommunities();
    fetchLeaderboard();
  }, []);

  const fetchCommunities = async () => {
    try {
      const response = await axios.get(`${API}/communities`);
      setCommunities(response.data);
    } catch (error) {
      console.error('Failed to fetch communities:', error);
    }
  };

  const fetchLeaderboard = async () => {
    try {
      const response = await axios.get(`${API}/leaderboard`);
      setLeaderboard(response.data);
    } catch (error) {
      console.error('Failed to fetch leaderboard:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-white text-xl">Loading community...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 pt-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">
            Community Hub
          </h1>
          <p className="text-xl text-gray-400 max-w-3xl mx-auto">
            Connect with fellow athletes, share your progress, and climb the leaderboard.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Leaderboard */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            className="lg:col-span-2 bg-gray-800 rounded-xl p-6"
          >
            <div className="flex items-center mb-6">
              <Trophy className="text-yellow-500 mr-3" size={24} />
              <h2 className="text-2xl font-bold text-white">Global Leaderboard</h2>
            </div>
            
            <div className="space-y-4">
              {leaderboard.map((user, index) => (
                <div
                  key={user.username}
                  className={`flex items-center justify-between p-4 rounded-lg ${
                    index < 3 ? 'bg-gradient-to-r from-yellow-500/20 to-orange-500/20' : 'bg-gray-700'
                  }`}
                >
                  <div className="flex items-center">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold mr-4 ${
                      index === 0 ? 'bg-yellow-500 text-black' :
                      index === 1 ? 'bg-gray-400 text-black' :
                      index === 2 ? 'bg-yellow-600 text-black' : 'bg-gray-600 text-white'
                    }`}>
                      {user.rank}
                    </div>
                    <div>
                      <h3 className="font-semibold text-white">{user.username}</h3>
                      <p className="text-sm text-gray-400">
                        {user.university && `${user.university} • `}{user.city}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-white">{user.points} pts</div>
                    {index < 3 && (
                      <div className="text-xs text-yellow-500">🏆</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Community Features */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            className="space-y-6"
          >
            <div className="bg-gray-800 rounded-xl p-6">
              <h3 className="text-xl font-bold text-white mb-4">Join Communities</h3>
              <p className="text-gray-400 mb-4">
                Connect with athletes from your university or city.
              </p>
              <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-semibold transition-colors w-full">
                Find My Community
              </button>
            </div>

            <div className="bg-gray-800 rounded-xl p-6">
              <h3 className="text-xl font-bold text-white mb-4">Real-time Chat</h3>
              <p className="text-gray-400 mb-4">
                Share tips, ask questions, and motivate each other.
              </p>
              <button className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg font-semibold transition-colors w-full">
                Join Chat
              </button>
            </div>

            <div className="bg-gray-800 rounded-xl p-6">
              <h3 className="text-xl font-bold text-white mb-4">Challenges</h3>
              <p className="text-gray-400 mb-4">
                Participate in monthly challenges and earn badges.
              </p>
              <button className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg font-semibold transition-colors w-full">
                View Challenges
              </button>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

// Contact Page
const ContactPage = () => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    subject: '',
    message: ''
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    toast.success('Message sent! We\'ll get back to you soon.');
    setFormData({ name: '', email: '', subject: '', message: '' });
  };

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  return (
    <div className="min-h-screen bg-gray-900 pt-20">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">
            Get in Touch
          </h1>
          <p className="text-xl text-gray-400 max-w-3xl mx-auto">
            Have questions about your fitness journey? We're here to help.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <h2 className="text-2xl font-bold text-white mb-6">Contact Information</h2>
            
            <div className="space-y-6">
              <div className="flex items-center">
                <MessageCircle className="text-blue-400 mr-4" size={24} />
                <div>
                  <h3 className="font-semibold text-white">Email</h3>
                  <p className="text-gray-400">support@dominion.fitness</p>
                </div>
              </div>
              
              <div className="flex items-center">
                <Users className="text-blue-400 mr-4" size={24} />
                <div>
                  <h3 className="font-semibold text-white">Community</h3>
                  <p className="text-gray-400">Join our Discord server</p>
                </div>
              </div>
              
              <div className="flex items-center">
                <Heart className="text-blue-400 mr-4" size={24} />
                <div>
                  <h3 className="font-semibold text-white">Social Media</h3>
                  <p className="text-gray-400">Follow us @dominion_fitness</p>
                </div>
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            className="bg-gray-800 rounded-xl p-8"
          >
            <h2 className="text-2xl font-bold text-white mb-6">Send us a Message</h2>
            
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label className="text-gray-300">Name</label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  className="w-full mt-2 p-3 bg-gray-700 text-white rounded-lg border border-gray-600 focus:border-blue-500 focus:outline-none"
                  required
                />
              </div>
              
              <div>
                <label className="text-gray-300">Email</label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  className="w-full mt-2 p-3 bg-gray-700 text-white rounded-lg border border-gray-600 focus:border-blue-500 focus:outline-none"
                  required
                />
              </div>
              
              <div>
                <label className="text-gray-300">Subject</label>
                <input
                  type="text"
                  name="subject"
                  value={formData.subject}
                  onChange={handleChange}
                  className="w-full mt-2 p-3 bg-gray-700 text-white rounded-lg border border-gray-600 focus:border-blue-500 focus:outline-none"
                  required
                />
              </div>
              
              <div>
                <label className="text-gray-300">Message</label>
                <textarea
                  name="message"
                  value={formData.message}
                  onChange={handleChange}
                  rows={6}
                  className="w-full mt-2 p-3 bg-gray-700 text-white rounded-lg border border-gray-600 focus:border-blue-500 focus:outline-none resize-none"
                  required
                />
              </div>
              
              <button
                type="submit"
                className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-lg font-semibold transition-colors"
              >
                Send Message
              </button>
            </form>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-white text-xl">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

// Router Component
const AppRouter = () => {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/exercises" element={<ExercisesPage />} />
      <Route path="/exercises/:exerciseId" element={<ExerciseDetailWrapper />} />
      <Route path="/progression" element={<ProgressionPage />} />
      <Route path="/community" element={<CommunityPage />} />
      <Route path="/shop" element={<ShopPage />} />
      <Route path="/contact" element={<ContactPage />} />
    </Routes>
  );
};

// Wrapper for exercise detail to get params
const ExerciseDetailWrapper = () => {
  const { exerciseId } = useParams();
  return <ExerciseDetailPage exerciseId={exerciseId} />;
};

// Import useParams for wrapper
import { useParams } from 'react-router-dom';

// Main App Component
function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="App">
          <Header />
          <main>
            <AppRouter />
          </main>
          <Toaster 
            position="top-right"
            toastOptions={{
              style: {
                background: '#374151',
                color: '#fff',
              },
            }}
          />
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;
