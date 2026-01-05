import { useState, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const API_URL = 'http://localhost:8000'

// Icons as components
const UploadIcon = () => (
  <svg viewBox="0 0 24 24">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="17 8 12 3 7 8" />
    <line x1="12" y1="3" x2="12" y2="15" />
  </svg>
)

const FileIcon = () => (
  <svg viewBox="0 0 24 24">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="16" y1="13" x2="8" y2="13" />
    <line x1="16" y1="17" x2="8" y2="17" />
    <polyline points="10 9 9 9 8 9" />
  </svg>
)

const CheckIcon = () => (
  <svg viewBox="0 0 24 24">
    <polyline points="20 6 9 17 4 12" />
  </svg>
)

const DownloadIcon = () => (
  <svg viewBox="0 0 24 24">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="7 10 12 15 17 10" />
    <line x1="12" y1="15" x2="12" y2="3" />
  </svg>
)

const RefreshIcon = () => (
  <svg viewBox="0 0 24 24">
    <polyline points="23 4 23 10 17 10" />
    <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
  </svg>
)

const AlertIcon = () => (
  <svg viewBox="0 0 24 24">
    <circle cx="12" cy="12" r="10" />
    <line x1="12" y1="8" x2="12" y2="12" />
    <line x1="12" y1="16" x2="12.01" y2="16" />
  </svg>
)

function App() {
  const [state, setState] = useState('idle') // idle, processing, success, error
  const [file, setFile] = useState(null)
  const [progress, setProgress] = useState(0)
  const [progressStep, setProgressStep] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [isDragging, setIsDragging] = useState(false)
  const [correctedBlob, setCorrectedBlob] = useState(null)
  const fileInputRef = useRef(null)

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / 1048576).toFixed(1) + ' MB'
  }

  const simulateProgress = (callback) => {
    const steps = [
      { progress: 20, step: 'Extracting text...' },
      { progress: 45, step: 'Analyzing content...' },
      { progress: 70, step: 'Applying corrections...' },
      { progress: 90, step: 'Rebuilding document...' },
    ]
    
    let i = 0
    const interval = setInterval(() => {
      if (i < steps.length) {
        setProgress(steps[i].progress)
        setProgressStep(steps[i].step)
        i++
      } else {
        clearInterval(interval)
        callback()
      }
    }, 800)
    
    return interval
  }

  const processFile = async (uploadedFile) => {
    setFile(uploadedFile)
    setState('processing')
    setProgress(0)
    setProgressStep('Starting...')
    setError(null)

    const formData = new FormData()
    formData.append('file', uploadedFile)

    // Start progress animation
    const progressInterval = simulateProgress(() => {})

    try {
      // First, get the preview with changes
      const previewRes = await fetch(`${API_URL}/preview`, {
        method: 'POST',
        body: formData,
      })

      if (!previewRes.ok) {
        const err = await previewRes.json()
        throw new Error(err.detail || 'Failed to process document')
      }

      const previewData = await previewRes.json()

      // Now get the corrected file
      const fileFormData = new FormData()
      fileFormData.append('file', uploadedFile)
      
      const fileRes = await fetch(`${API_URL}/upload`, {
        method: 'POST',
        body: fileFormData,
      })

      if (!fileRes.ok) {
        const err = await fileRes.json()
        throw new Error(err.detail || 'Failed to generate corrected file')
      }

      const blob = await fileRes.blob()
      setCorrectedBlob(blob)

      clearInterval(progressInterval)
      setProgress(100)
      setProgressStep('Complete!')
      
      setTimeout(() => {
        setResult(previewData)
        setState('success')
      }, 500)

    } catch (err) {
      clearInterval(progressInterval)
      setError(err.message)
      setState('error')
    }
  }

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setIsDragging(false)
    
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile) {
      processFile(droppedFile)
    }
  }, [])

  const handleDragOver = useCallback((e) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      processFile(selectedFile)
    }
  }

  const handleClick = () => {
    fileInputRef.current?.click()
  }

  const handleDownload = () => {
    if (correctedBlob && file) {
      const url = URL.createObjectURL(correctedBlob)
      const a = document.createElement('a')
      a.href = url
      a.download = `corrected_${file.name}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }
  }

  const handleReset = () => {
    setState('idle')
    setFile(null)
    setProgress(0)
    setResult(null)
    setError(null)
    setCorrectedBlob(null)
  }

  return (
    <div className="app">
      {/* Header */}
      <motion.header 
        className="header"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <h1 className="logo">R<em>e</em>fine</h1>
        <p className="tagline">
          AI-powered document correction for spelling, grammar, and factual accuracy
        </p>
      </motion.header>

      <AnimatePresence mode="wait">
        {/* Upload State */}
        {state === 'idle' && (
          <motion.div
            key="upload"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.3 }}
            className={`upload-zone ${isDragging ? 'dragging' : ''}`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={handleClick}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileSelect}
              accept=".pdf,.xlsx,.docx,.txt"
              style={{ display: 'none' }}
            />
            <div className="upload-content">
              <div className="upload-icon">
                <UploadIcon />
              </div>
              <h2 className="upload-title">Drop your document</h2>
              <p className="upload-subtitle">or click to browse files</p>
              <div className="upload-formats">
                <span className="format-badge">PDF</span>
                <span className="format-badge">XLSX</span>
                <span className="format-badge">DOCX</span>
                <span className="format-badge">TXT</span>
              </div>
            </div>
          </motion.div>
        )}

        {/* Processing State */}
        {state === 'processing' && (
          <motion.div
            key="processing"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.3 }}
            className="processing-container"
          >
            <div className="processing-card">
              <div className="file-info">
                <div className="file-icon">
                  <FileIcon />
                </div>
                <div className="file-details">
                  <div className="file-name">{file?.name}</div>
                  <div className="file-size">{formatFileSize(file?.size || 0)}</div>
                </div>
              </div>
              
              <div className="spinner" />
              <p className="processing-text">Processing your document</p>
              <p className="processing-step">{progressStep}</p>
              
              <div className="progress-container">
                <div className="progress-label">
                  <span>Progress</span>
                  <span>{progress}%</span>
                </div>
                <div className="progress-bar">
                  <motion.div 
                    className="progress-fill"
                    initial={{ width: 0 }}
                    animate={{ width: `${progress}%` }}
                    transition={{ duration: 0.3 }}
                  />
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* Success State */}
        {state === 'success' && result && (
          <motion.div
            key="success"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.4 }}
            className="results-container"
          >
            <div className="results-header">
              <h2 className="results-title">
                <span className="success-icon">
                  <CheckIcon />
                </span>
                Corrections Applied
              </h2>
              <div className="results-actions">
                <button className="btn btn-secondary" onClick={handleReset}>
                  <RefreshIcon />
                  New File
                </button>
                <button className="btn btn-primary" onClick={handleDownload}>
                  <DownloadIcon />
                  Download
                </button>
              </div>
            </div>

            {/* Summary */}
            {result.summary && (
              <motion.div 
                className="changes-summary"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
              >
                <p className="summary-text">{result.summary}</p>
              </motion.div>
            )}

            {/* Changes List */}
            {result.changes && result.changes.length > 0 && (
              <motion.div 
                className="changes-list"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                <div className="changes-header">
                  {result.changes.length} Correction{result.changes.length !== 1 ? 's' : ''} Made
                </div>
                {result.changes.slice(0, 10).map((change, idx) => (
                  <motion.div 
                    key={idx} 
                    className="change-item"
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.1 + idx * 0.05 }}
                  >
                    <span className={`change-type ${change.type}`}>{change.type}</span>
                    <div className="change-text">
                      <span className="original">{change.original}</span>
                      <span className="arrow">→</span>
                      <span className="corrected">{change.corrected}</span>
                    </div>
                    {change.explanation && (
                      <p className="change-explanation">{change.explanation}</p>
                    )}
                  </motion.div>
                ))}
                {result.changes.length > 10 && (
                  <div className="change-item" style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                    + {result.changes.length - 10} more corrections
                  </div>
                )}
              </motion.div>
            )}

            {/* Preview Panels */}
            <motion.div 
              className="preview-container"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <div className="preview-panel">
                <div className="preview-header">Original</div>
                <div className="preview-content original-text">
                  {result.original?.slice(0, 2000)}
                  {result.original?.length > 2000 && '...'}
                </div>
              </div>
              <div className="preview-panel">
                <div className="preview-header">Corrected</div>
                <div className="preview-content corrected-text">
                  {result.corrected?.slice(0, 2000)}
                  {result.corrected?.length > 2000 && '...'}
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}

        {/* Error State */}
        {state === 'error' && (
          <motion.div
            key="error"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.3 }}
            className="error-container"
          >
            <div className="error-card">
              <div className="error-icon">
                <AlertIcon />
              </div>
              <h2 className="error-title">Something went wrong</h2>
              <p className="error-message">{error}</p>
              <button className="btn btn-primary" onClick={handleReset}>
                Try Again
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default App

