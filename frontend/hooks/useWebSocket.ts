import { useEffect, useRef } from 'react';
import { useSystemStore } from '../store/systemStore';

// Use environment variable for production WebSocket URL, fallback to localhost for dev
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws';

export function useWebSocket() {
  const ws = useRef<WebSocket | null>(null);
  const { 
    setConnectionStatus, 
    setInitialState,
    resetState,
    addIncident, 
    updateIncident, 
    updateResources, 
    addDispatch, 
    addAlert, 
    addFeedEvents, 
    updateReasoning 
  } = useSystemStore();

  useEffect(() => {
    let reconnectInterval: NodeJS.Timeout;

    const connect = () => {
      ws.current = new WebSocket(WS_URL);

      ws.current.onopen = () => {
        console.log('Connected to CrisisGrid AI WS');
        setConnectionStatus(true);
      };

      ws.current.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          
          switch (payload.type) {
            case 'state_snapshot':
              setInitialState(payload.data);
              break;
            case 'incident':
              // Check if it's an update or new
              // Our store handles it gracefully with filter
              addIncident(payload.data);
              break;
            case 'dispatch':
              addDispatch(payload.data);
              break;
            case 'resources':
              updateResources(payload.data);
              break;
            case 'alert':
              addAlert(payload.data.message);
              break;
            case 'feed':
              addFeedEvents(payload.data);
              break;
            case 'reasoning':
              updateReasoning(payload.data);
              break;
            case 'heartbeat':
              // Just keep alive
              break;
            case 'system':
              if (payload.event === 'system_reset') {
                // Immediately clear all frontend state
                // The subsequent state_snapshot will repopulate with clean data
                resetState();
                console.log('System reset — frontend state cleared');
              }
              break;
            default:
              console.log('Unknown WS event:', payload);
          }
        } catch (err) {
          console.error('Failed to parse WS message', err);
        }
      };

      ws.current.onclose = () => {
        console.log('Disconnected from CrisisGrid AI WS');
        setConnectionStatus(false);
        // Reconnect after 3 seconds
        reconnectInterval = setTimeout(connect, 3000);
      };
      
      ws.current.onerror = (error) => {
        console.error('WebSocket Error', error);
        ws.current?.close();
      };
    };

    connect();

    return () => {
      clearTimeout(reconnectInterval);
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [
    setConnectionStatus,
    setInitialState,
    resetState,
    addIncident,
    updateResources,
    addDispatch,
    addAlert,
    addFeedEvents,
    updateReasoning
  ]);

  return ws.current;
}
