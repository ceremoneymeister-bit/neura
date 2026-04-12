import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { WifiOff, Wifi } from 'lucide-react'

type Status = 'online' | 'offline' | 'restored'

export function NetworkStatus() {
  const [status, setStatus] = useState<Status>('online')

  useEffect(() => {
    const handleOffline = () => setStatus('offline')
    const handleOnline = () => {
      setStatus('restored')
      setTimeout(() => setStatus('online'), 2000)
    }

    window.addEventListener('offline', handleOffline)
    window.addEventListener('online', handleOnline)

    // Check initial state
    if (!navigator.onLine) setStatus('offline')

    return () => {
      window.removeEventListener('offline', handleOffline)
      window.removeEventListener('online', handleOnline)
    }
  }, [])

  return (
    <AnimatePresence>
      {status !== 'online' && (
        <motion.div
          initial={{ y: -40, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -40, opacity: 0 }}
          transition={{ duration: 0.2 }}
          className={`fixed top-0 left-0 right-0 z-[200] flex items-center justify-center gap-2 py-1.5 text-xs font-medium ${
            status === 'offline'
              ? 'bg-amber-500/90 text-black'
              : 'bg-emerald-500/90 text-white'
          }`}
        >
          {status === 'offline' ? (
            <>
              <WifiOff size={13} />
              <span>Нет соединения</span>
            </>
          ) : (
            <>
              <Wifi size={13} />
              <span>Подключено</span>
            </>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  )
}
