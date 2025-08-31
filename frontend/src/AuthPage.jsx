import { useState } from "react";
import { Shield, Zap, Brain, BarChart } from "lucide-react";

export default function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);

  return (
    <div className="relative flex flex-col min-h-screen overflow-hidden bg-app">
      
      {/* 🔹 Top Header */}
      <header className="w-full py-4 shadow-md bg-gradient-to-r from-blue-600 to-cyan-500">
        <div className="flex flex-col items-center justify-center text-center">
          <h1 className="text-2xl font-bold text-white md:text-3xl drop-shadow-lg">
            Automation
          </h1>
          <p className="mt-1 text-sm italic text-white/90">
            Smarter growth. AI-powered efficiency 🚀
          </p>
        </div>
      </header>

      {/* 🔹 Centered container */}
      <div className="flex items-center justify-center flex-1 px-4 py-8">
        <div className="card w-[350px] md:w-[420px] max-h-[80vh] overflow-y-auto animate-fade-in">
          
          {/* Toggle Tabs */}
          <div className="flex mb-6 overflow-hidden border rounded-xl border-white/30">
            <button
              onClick={() => setIsLogin(true)}
              className={isLogin ? "btn-toggle-active" : "btn-toggle-inactive"}
            >
              Login
            </button>
            <button
              onClick={() => setIsLogin(false)}
              className={!isLogin ? "btn-toggle-active" : "btn-toggle-inactive"}
            >
              Signup
            </button>
          </div>

          {/* Forms */}
          {isLogin ? (
            <form className="space-y-4">
              <input type="email" placeholder="Enter your email" className="input" />
              <input type="password" placeholder="Enter your password" className="input" />
              <button className="btn-primary">Login</button>
            </form>
          ) : (
            <form className="space-y-4">
              <input type="text" placeholder="Enter your name" className="input" />
              <input type="email" placeholder="Enter your email" className="input" />
              <input type="password" placeholder="Create a password" className="input" />
              <button className="btn-primary">Sign Up</button>
            </form>
          )}

          {/* Divider */}
          <div className="flex items-center my-5">
            <div className="flex-1 h-px bg-white/30"></div>
            <span className="px-3 text-sm text-gray-600">or continue with</span>
            <div className="flex-1 h-px bg-white/30"></div>
          </div>

          {/* OAuth Buttons */}
          <div className="flex justify-center gap-4">
            <button className="btn-oauth">
              <img
                src="https://developers.google.com/identity/images/g-logo.png"
                alt="Google"
                className="w-5 h-5"
              />
              <span className="text-sm font-medium">Google</span>
            </button>

            <button className="btn-oauth">
              <img
                src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"
                alt="GitHub"
                className="w-5 h-5"
              />
              <span className="text-sm font-medium">GitHub</span>
            </button>
          </div>
        </div>
      </div>

      {/* 🔹 Footer */}
      <footer className="px-6 py-3 text-white border-t bg-gradient-to-r from-blue-600 to-cyan-500 border-white/20">
        <div className="flex items-center justify-between w-full max-w-5xl mx-auto text-sm">
          <div className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-white" />
            <span className="text-white">AI Powered</span>
          </div>
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-white" />
            <span className="text-white">Secure</span>
          </div>
          <div className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-white" />
            <span className="text-white">Fast Growth</span>
          </div>
          <div className="flex items-center gap-2">
            <BarChart className="w-5 h-5 text-white" />
            <span className="text-white">Analytics Ready</span>
          </div>
        </div>
      </footer>

    </div>
  );
}
