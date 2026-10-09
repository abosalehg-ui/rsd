/**
 * رصد - ثوابت مشتركة بين طبقات الخريطة (`RasadMap` ووحدات `layers/`).
 */

// عتبة تجميع النقاط بالبكسل على الشاشة (انظر clusterEvents في RasadMap)
export const CLUSTER_PX = 42;

// ترتيب الرسم في Leaflet — الضربات والمنشآت فوق نقاط الأحداث دائماً
export const Z_OFFSET = { iran: 400, nuclear: 300, base: 200, event: 0, flight: -100 };

export const NO_NUDGE = { dx: 0, dy: 0 };
