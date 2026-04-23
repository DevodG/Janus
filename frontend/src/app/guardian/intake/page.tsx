'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Shield, Upload, Link, MessageSquare } from 'lucide-react';

import { guardianClient } from '@/lib/api';

export default function IntakePage() {
  const [text, setText] = useState('');
  const [url, setUrl] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleAnalyze = async () => {
    setLoading(true);
    try {
      let imageBase64 = undefined;
      if (file) {
        imageBase64 = await toBase64(file);
      }

      const data = await guardianClient.analyze({
        text,
        url,
        image_base64: imageBase64,
        source: 'manual_intake'
      });

      router.push(`/guardian/result/${data.id}`);
    } catch (error) {
      console.error('Analysis failed', error);
      alert('Analysis failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const toBase64 = (file: File) => new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = error => reject(error);
  });

  return (
    <div className="max-w-4xl mx-auto py-12 px-6">
      <div className="flex items-center gap-4 mb-8">
        <div className="p-3 bg-blue-600/20 rounded-xl">
          <Shield className="w-8 h-8 text-blue-500" />
        </div>
        <div>
          <h1 className="text-3xl font-bold">Scam Intake Hub</h1>
          <p className="text-gray-400">Submit suspicious messages, links, or screenshots for immediate forensic analysis.</p>
        </div>
      </div>

      <div className="grid gap-6">
        {/* Text Input */}
        <div className="bg-gray-900/50 border border-gray-800 p-6 rounded-2xl">
          <div className="flex items-center gap-3 mb-4">
            <MessageSquare className="w-5 h-5 text-gray-400" />
            <h2 className="font-semibold">Text Content</h2>
          </div>
          <textarea
            className="w-full bg-black/40 border border-gray-800 rounded-xl p-4 min-h-[150px] focus:border-blue-500 outline-none transition-colors"
            placeholder="Paste the SMS, Email, or WhatsApp message here..."
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          {/* URL Input */}
          <div className="bg-gray-900/50 border border-gray-800 p-6 rounded-2xl">
            <div className="flex items-center gap-3 mb-4">
              <Link className="w-5 h-5 text-gray-400" />
              <h2 className="font-semibold">Suspicious URL</h2>
            </div>
            <input
              type="text"
              className="w-full bg-black/40 border border-gray-800 rounded-xl p-4 focus:border-blue-500 outline-none transition-colors"
              placeholder="https://paytm-kyc-verify.xyz"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
          </div>

          {/* Screenshot Upload */}
          <div className="bg-gray-900/50 border border-gray-800 p-6 rounded-2xl">
            <div className="flex items-center gap-3 mb-4">
              <Upload className="w-5 h-5 text-gray-400" />
              <h2 className="font-semibold">Evidence Screenshot</h2>
            </div>
            <input
              type="file"
              className="hidden"
              id="file-upload"
              accept="image/*"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
            <label
              htmlFor="file-upload"
              className="flex flex-col items-center justify-center border-2 border-dashed border-gray-800 rounded-xl p-6 cursor-pointer hover:border-gray-600 transition-colors"
            >
              <Upload className="w-8 h-8 text-gray-500 mb-2" />
              <span className="text-gray-400">{file ? file.name : 'Click to upload proof'}</span>
            </label>
          </div>
        </div>

        <button
          onClick={handleAnalyze}
          disabled={loading || (!text && !url && !file)}
          className={`w-full py-4 rounded-xl font-bold text-lg transition-all ${
            loading || (!text && !url && !file)
              ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-900/20'
          }`}
        >
          {loading ? 'Analyzing Signals...' : 'Run Forensic Intelligence Scan'}
        </button>
      </div>
    </div>
  );
}
