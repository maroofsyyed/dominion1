import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { motion } from 'framer-motion';
import { Menu, X, User, Dumbbell, Users, ShoppingBag, Activity, Brain } from 'lucide-react';
import './App.css';

function App() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);

  useEffect(() => {
    // Check authentication status
    const token = localStorage.getItem('token');
    if (token) {
      setIsAuthenticated(true);
      // Fetch user data
    }
  }, []);

  const navigationItems = [
    { path: '/exercises', icon: <Dumbbell size={20} />, text: 'Exercises' },
    { path: '/community', icon: <Users size={20} />, text: 'Community' },
    { path: '/shop', icon: <ShoppingBag size={20} />, text: 'Shop' },
    { path: '/progress', icon: <Activity size={20} />, text: 'Progress' },
    { path: '/mobility', icon: <Brain size={20} />, text: 'Mobility' },
  ];

  return (
    <Router>
      <div className="min-h-screen bg-gray-900">
        <Toaster position="top-right" />
        
        {/* Navigation */}
        <nav className="bg-gray-800 fixed w-full z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center">
                <Link to="/" className="flex items-center">
                  <span className="text-2xl font-bold text-white">Dominion</span>
                </Link>
              </div>

              {/* Desktop Navigation */}
              <div className="hidden md:block">
                <div className="flex items-center space-x-4">
                  {navigationItems.map((item) => (
                    <Link
                      key={item.path}
                      to={item.path}
                      className="text-gray-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium flex items-center space-x-2"
                    >
                      {item.icon}
                      <span>{item.text}</span>
                    </Link>
                  ))}
                  
                  {isAuthenticated ? (
                    <Link
                      to="/profile"
                      className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium flex items-center space-x-2"
                    >
                      <User size={20} />
                      <span>Profile</span>
                    </Link>
                  ) : (
                    <Link
                      to="/login"
                      className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium"
                    >
                      Login
                    </Link>
                  )}
                </div>
              </div>

              {/* Mobile menu button */}
              <div className="md:hidden">
                <button
                  onClick={() => setIsMenuOpen(!isMenuOpen)}
                  className="text-gray-400 hover:text-white focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-800 focus:ring-white"
                >
                  {isMenuOpen ? <X size={24} /> : <Menu size={24} />}
                </button>
              </div>
            </div>
          </div>

          {/* Mobile menu */}
          {isMenuOpen && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="md:hidden bg-gray-800"
            >
              <div className="px-2 pt-2 pb-3 space-y-1 sm:px-3">
                {navigationItems.map((item) => (
                  <Link
                    key={item.path}
                    to={item.path}
                    className="text-gray-300 hover:text-white block px-3 py-2 rounded-md text-base font-medium flex items-center space-x-2"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    {item.icon}
                    <span>{item.text}</span>
                  </Link>
                ))}
              </div>
            </motion.div>
          )}
        </nav>

        {/* Main Content */}
        <main className="pt-16">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/exercises" element={<Exercises />} />
            <Route path="/community" element={<Community />} />
            <Route path="/shop" element={<Shop />} />
            <Route path="/progress" element={<Progress />} />
            <Route path="/mobility" element={<Mobility />} />
            <Route path="/login" element={<Login />} />
            <Route path="/profile" element={<Profile />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

// Home Component
function Home() {
  return (
    <div className="relative">
      {/* Hero Section */}
      <div className="relative bg-gray-900 overflow-hidden">
        <div className="max-w-7xl mx-auto">
          <div className="relative z-10 pb-8 bg-gray-900 sm:pb-16 md:pb-20 lg:max-w-2xl lg:w-full lg:pb-28 xl:pb-32">
            <main className="mt-10 mx-auto max-w-7xl px-4 sm:mt-12 sm:px-6 md:mt-16 lg:mt-20 lg:px-8 xl:mt-28">
              <div className="sm:text-center lg:text-left">
                <motion.h1
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5 }}
                  className="text-4xl tracking-tight font-extrabold text-white sm:text-5xl md:text-6xl"
                >
                  <span className="block">Master Your Body</span>
                  <span className="block text-blue-600">Master Your Life</span>
                </motion.h1>
                <motion.p
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.2 }}
                  className="mt-3 text-base text-gray-300 sm:mt-5 sm:text-lg sm:max-w-xl sm:mx-auto md:mt-5 md:text-xl lg:mx-0"
                >
                  Start your calisthenics journey with Dominion. Progressive workouts, expert guidance, and a supportive community.
                </motion.p>
                <div className="mt-5 sm:mt-8 sm:flex sm:justify-center lg:justify-start">
                  <motion.div
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.5, delay: 0.4 }}
                  >
                    <Link
                      to="/exercises"
                      className="w-full flex items-center justify-center px-8 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 md:py-4 md:text-lg md:px-10"
                    >
                      Get Started
                    </Link>
                  </motion.div>
                </div>
              </div>
            </main>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="py-12 bg-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h2 className="text-3xl font-extrabold text-white sm:text-4xl">
              Why Choose Dominion?
            </h2>
            <p className="mt-4 text-xl text-gray-300">
              Everything you need to achieve your fitness goals
            </p>
          </div>

          <div className="mt-10">
            <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
              {/* Feature cards */}
              <FeatureCard
                title="Progressive System"
                description="Follow our proven progression system across 6 fundamental movement patterns"
                icon={<Dumbbell className="h-6 w-6 text-blue-500" />}
              />
              <FeatureCard
                title="Expert Guidance"
                description="Learn proper form and technique with detailed instructions and tips"
                icon={<Brain className="h-6 w-6 text-blue-500" />}
              />
              <FeatureCard
                title="Community Support"
                description="Join a community of like-minded individuals on the same journey"
                icon={<Users className="h-6 w-6 text-blue-500" />}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Feature Card Component
function FeatureCard({ title, description, icon }) {
  return (
    <motion.div
      whileHover={{ scale: 1.05 }}
      className="bg-gray-700 rounded-lg p-6"
    >
      <div className="flex items-center justify-center h-12 w-12 rounded-md bg-gray-800 text-white">
        {icon}
      </div>
      <div className="mt-6">
        <h3 className="text-lg font-medium text-white">{title}</h3>
        <p className="mt-2 text-base text-gray-300">{description}</p>
      </div>
    </motion.div>
  );
}

// Placeholder Components
function Exercises() {
  return <div className="p-4 text-white">Exercises Component</div>;
}

function Community() {
  return <div className="p-4 text-white">Community Component</div>;
}

function Shop() {
  return <div className="p-4 text-white">Shop Component</div>;
}

function Progress() {
  return <div className="p-4 text-white">Progress Component</div>;
}

function Mobility() {
  return <div className="p-4 text-white">Mobility Component</div>;
}

function Login() {
  return <div className="p-4 text-white">Login Component</div>;
}

function Profile() {
  return <div className="p-4 text-white">Profile Component</div>;
}

export default App;