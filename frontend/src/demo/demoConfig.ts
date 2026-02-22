/**
 * demoConfig.ts — Demo mode flag, isolated to break the circular dependency
 * between useBlitzStore and demoPlayer.
 */
export const IS_DEMO_MODE = import.meta.env.VITE_DEMO_MODE === 'cached'
