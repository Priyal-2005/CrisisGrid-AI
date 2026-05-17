import { useEffect, useRef } from 'react';
import { useSystemStore } from '../store/systemStore';

const WS_URL = 'ws://localhost:8000/ws';

export function useWebSocket() {
  const ws = useRef<WebSocket | null>(null);
  const { 
    setConnectionStatus, 
    setInitialState, 
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
                // Let the next state_snapshot handle the actual reset data
                console.log('System reset triggered');
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
    addIncident,
    updateResources,
    addDispatch,
    addAlert,
    addFeedEvents,
    updateReasoning
  ]);

  return ws.current;
}
