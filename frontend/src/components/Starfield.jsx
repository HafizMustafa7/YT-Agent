import React from 'react';
import { motion } from 'framer-motion';

const Starfield = () => (
  <div className="fixed inset-0 overflow-hidden pointer-events-none">
    {[...Array(100)].map((_, i) => (
      <motion.div
        key={i}
        className="absolute w-1 h-1 bg-white rounded-full opacity-60"
        style={{
          left: `${Math.random() * 100}%`,
          top: `${Math.random() * 100}%`,
        }}
        animate={{
          y: [0, -20, 0],
          opacity: [0.6, 1, 0.6],
        }}
        transition={{
          duration: Math.random() * 10 + 5,
          repeat: Infinity,
          delay: Math.random() * 2,
        }}
      />
    ))}
  </div>
);

export default Starfield;
