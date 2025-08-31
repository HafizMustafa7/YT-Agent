export default function AuthLayout({ children }) {
  return (
    <div className="flex items-center justify-center min-h-screen bg-app animate-gradient">
      <div className="relative card w-96 animate-fade-in">
        {/* Logo */}
        <div className="flex justify-center mb-6">
          <img
            src="https://upload.wikimedia.org/wikipedia/commons/b/b8/YouTube_Logo_2017.svg"
            alt="YouTube Logo"
            className="h-12 drop-shadow-md"
          />
        </div>

        {/* Injected content */}
        {children}
      </div>
    </div>
  );
}
