import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, CheckCircle2, AlertCircle, Loader2, Database, Search, FileText } from 'lucide-react';

const API_BASE = '/api';

const App = () => {
    const [file, setFile] = useState(null);
    const [jobId, setJobId] = useState(null);
    const [status, setStatus] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [isDragging, setIsDragging] = useState(false);

    const fetchStatus = useCallback(async () => {
        if (!jobId) return;
        try {
            const response = await axios.get(`${API_BASE}/status/${jobId}`);
            setStatus(response.data);
            if (response.data.status === 'completed' || response.data.status.startsWith('error')) {
                // Stop polling
            }
        } catch (err) {
            console.error('Failed to fetch status', err);
        }
    }, [jobId]);

    useEffect(() => {
        let interval;
        if (jobId && status?.status !== 'completed' && !status?.status?.startsWith('error')) {
            interval = setInterval(fetchStatus, 1000);
        }
        return () => clearInterval(interval);
    }, [jobId, status, fetchStatus]);

    const onDragOver = (e) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const onDragLeave = () => {
        setIsDragging(false);
    };

    const onDrop = (e) => {
        e.preventDefault();
        setIsDragging(false);
        const droppedFile = e.dataTransfer.files[0];
        if (droppedFile) setFile(droppedFile);
    };

    const handleUpload = async () => {
        if (!file) return;
        setLoading(true);
        setError(null);
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await axios.post(`${API_BASE}/upload`, formData);
            setJobId(response.data.job_id);
            setStatus({ status: 'starting', processed: 0, total: 0, percentage: 0 });
        } catch (err) {
            setError(err.response?.data?.error || 'Upload failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex flex-col items-center justify-center p-6 bg-background relative overflow-hidden">
            {/* Background blobs */}
            <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-primary/20 rounded-full blur-[120px] animate-pulse-slow"></div>
            <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-secondary/20 rounded-full blur-[120px] animate-pulse-slow"></div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="w-full max-w-2xl z-10"
            >
                <header className="mb-8 text-center">
                    <h1 className="text-5xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-secondary mb-2 tracking-tight">
                        WP Plugin Hunter
                    </h1>
                    <p className="text-gray-400 text-lg">High-speed WordPress vulnerability & plugin scanning</p>
                </header>

                <div className="glass rounded-3xl p-8 shadow-2xl relative">
                    {!jobId ? (
                        <div className="space-y-6">
                            <div
                                onDragOver={onDragOver}
                                onDragLeave={onDragLeave}
                                onDrop={onDrop}
                                className={`border-2 border-dashed rounded-2xl p-12 transition-all duration-300 flex flex-col items-center gap-4 cursor-pointer
                  ${isDragging ? 'border-primary bg-primary/10 scale-[1.02]' : 'border-gray-700 hover:border-gray-500 bg-white/5'}
                `}
                                onClick={() => document.getElementById('file-input').click()}
                            >
                                <input
                                    id="file-input"
                                    type="file"
                                    className="hidden"
                                    onChange={(e) => setFile(e.target.files[0])}
                                />
                                <div className="p-4 bg-primary/20 rounded-full glow-primary">
                                    <Upload className="w-8 h-8 text-primary" />
                                </div>
                                <div className="text-center">
                                    <p className="text-xl font-semibold mb-1">
                                        {file ? file.name : "Drop your domains file here"}
                                    </p>
                                    <p className="text-gray-400 text-sm">Supports .txt files with one domain per line</p>
                                </div>
                            </div>

                            {error && (
                                <div className="bg-red-500/10 border border-red-500/20 text-red-500 px-4 py-3 rounded-xl flex items-center gap-3">
                                    <AlertCircle className="w-5 h-5" />
                                    <span>{error}</span>
                                </div>
                            )}

                            <button
                                disabled={!file || loading}
                                onClick={handleUpload}
                                className={`w-full py-4 rounded-xl font-bold text-lg transition-all duration-300 flex items-center justify-center gap-2
                  ${!file || loading
                                        ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
                                        : 'bg-gradient-to-r from-primary to-secondary hover:scale-[1.02] active:scale-[0.98] glow-primary'
                                    }
                `}
                            >
                                {loading ? <Loader2 className="w-6 h-6 animate-spin" /> : "Start Hunting"}
                            </button>
                        </div>
                    ) : (
                        <div className="space-y-8">
                            <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-3">
                                    <Search className="w-5 h-5 text-primary" />
                                    <span className="font-semibold text-lg capitalize">{status?.status || 'Processing...'}</span>
                                </div>
                                <span className="bg-white/10 px-3 py-1 rounded-full text-sm font-medium border border-white/10 uppercase tracking-widest">
                                    Job ID: {jobId.split('-')[0]}
                                </span>
                            </div>

                            {/* Progress Bar Container */}
                            <div className="space-y-4">
                                <div className="h-6 bg-white/5 rounded-full overflow-hidden border border-white/5 p-1">
                                    <motion.div
                                        initial={{ width: 0 }}
                                        animate={{ width: `${status?.percentage || 0}%` }}
                                        className="h-full bg-gradient-to-r from-primary to-secondary rounded-full relative"
                                    >
                                        <div className="absolute inset-0 bg-white/20 animate-pulse"></div>
                                    </motion.div>
                                </div>
                                <div className="flex justify-between text-gray-400 font-medium">
                                    <span>{status?.processed || 0} / {status?.total || 0} Domains</span>
                                    <span className="text-primary font-bold">{status?.percentage || 0}%</span>
                                </div>
                            </div>

                            {/* Stats Grid */}
                            <div className="grid grid-cols-2 gap-4">
                                <div className="bg-white/5 p-4 rounded-2xl border border-white/5 flex items-center gap-4">
                                    <div className="p-3 bg-secondary/20 rounded-xl">
                                        <Database className="w-6 h-6 text-secondary" />
                                    </div>
                                    <div>
                                        <p className="text-xs text-gray-500 uppercase tracking-wider font-bold">New Hits</p>
                                        <p className="text-2xl font-bold">{status?.results_count || 0}</p>
                                    </div>
                                </div>
                                <div className="bg-white/5 p-4 rounded-2xl border border-white/5 flex items-center gap-4">
                                    <div className="p-3 bg-primary/20 rounded-xl">
                                        <FileText className="w-6 h-6 text-primary" />
                                    </div>
                                    <div>
                                        <p className="text-xs text-gray-500 uppercase tracking-wider font-bold">Target Sheet</p>
                                        <p className="text-sm font-bold truncate max-w-[120px]">{status?.tab_name || '... '}</p>
                                    </div>
                                </div>
                            </div>

                            {status?.status === 'completed' && (
                                <motion.div
                                    initial={{ opacity: 0, scale: 0.9 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    className="bg-green-500/10 border border-green-500/20 text-green-500 p-4 rounded-2xl flex items-center gap-4 glow-secondary"
                                >
                                    <CheckCircle2 className="w-8 h-8 flex-shrink-0" />
                                    <div>
                                        <p className="font-bold text-lg">Hunt Complete!</p>
                                        <p className="text-sm opacity-80">Results are now available in your Google Sheet.</p>
                                    </div>
                                </motion.div>
                            )}

                            <button
                                onClick={() => window.location.reload()}
                                className="w-full py-4 text-gray-400 hover:text-white transition-colors"
                            >
                                Start New Scan
                            </button>
                        </div>
                    )}
                </div>
            </motion.div>
        </div>
    );
};

export default App;
