'use client';

import { useState, useEffect, useRef } from 'react';

export default function Typewriter({ text, speed = 10 }: { text: string; speed?: number }) {
  const [displayed, setDisplayed] = useState('');
  const idx = useRef(0);

  useEffect(() => {
    idx.current = 0;
    setDisplayed('');
    const iv = setInterval(() => {
      if (idx.current < text.length) {
        setDisplayed(p => p + text[idx.current]);
        idx.current++;
      } else {
        clearInterval(iv);
      }
    }, speed);
    return () => clearInterval(iv);
  }, [text, speed]);

  return (
    <span>
      {displayed}
      {displayed.length < text.length && (
        <span className="inline-block w-0.5 h-4 bg-indigo-400 ml-0.5 animate-pulse" />
      )}
    </span>
  );
}
