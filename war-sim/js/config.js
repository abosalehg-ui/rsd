// ═══════════════════════════════════════
// config.js — Constants & Default Data
// ═══════════════════════════════════════

const WAR_START = new Date('2026-02-28');
const TODAY = new Date();
const WAR_DAY = Math.max(1, Math.ceil((TODAY - WAR_START) / 86400000));

// Default baseline (overridden by API)
const DEFAULT_DATA = {
  missiles: Math.max(0, 90 - Math.max(0, WAR_DAY - 25) * 2),
  launchers: Math.max(0, 150 - Math.max(0, WAR_DAY - 25) * 2),
  nuclear_pct: 15,
  airdef_pct: 10,
  navy_pct: 14,
  oil: 113,
  dead_iran: 1500 + Math.max(0, WAR_DAY - 25) * 40,
  dead_israel: 18,
  risk: 8,
  hormuz: 'مغلق جزئياً',
  likely: 'الإنهاك المتبادل',
  headline: '',
  military: '',
  diplomatic: '',
  economic: '',
  key_development: '',
  scenarios: null, // filled by AI
};

// Fallback scenarios if API fails
const FALLBACK_SCENARIOS = [
  {id:1,name:'الإنهاك المتبادل',en:'Mutual Exhaustion',prob:40,color:'#F59E0B',icon:'⚖️',
   desc:'تستمر الضربات بكثافة أقل حتى تنفد صواريخ إيران. أمريكا تعلن النصر بدون اتفاق رسمي.',
   oil:'$90-100',hormuz:'يفتح جزئياً',regime:'مجتبى خامنئي يبقى',nuke:'مدمر 85%+',
   events:[{d:WAR_DAY+5,e:'إيران < 5 صواريخ/يوم'},{d:WAR_DAY+10,e:'ترامب: المهمة شبه منجزة'},{d:WAR_DAY+17,e:'سحب حاملة طائرات'},{d:WAR_DAY+30,e:'هرمز يفتح بمرافقة'},{d:WAR_DAY+45,e:'انتهاء الضربات'}]},
  {id:2,name:'اتفاق تفاوضي',en:'Negotiated Deal',prob:25,color:'#10B981',icon:'🤝',
   desc:'وساطة دولية تنجح. وقف إطلاق نار مع ضمانات أمنية مقابل تنازلات نووية.',
   oil:'$75-85',hormuz:'مفتوح',regime:'إصلاحات',nuke:'تفكيك بإشراف دولي',
   events:[{d:WAR_DAY+3,e:'تواصل غير مباشر عبر وسيط'},{d:WAR_DAY+10,e:'محادثات سرية'},{d:WAR_DAY+20,e:'إعلان هدنة مؤقتة'},{d:WAR_DAY+35,e:'وقف إطلاق نار'},{d:WAR_DAY+60,e:'اتفاق إطاري'}]},
  {id:3,name:'انهيار النظام',en:'Regime Collapse',prob:15,color:'#A855F7',icon:'💥',
   desc:'احتجاجات داخلية + انشقاقات في الحرس الثوري. النظام ينهار من الداخل.',
   oil:'$120-140',hormuz:'فوضى ثم يفتح',regime:'ينهار',nuke:'تأمين دولي',
   events:[{d:WAR_DAY+10,e:'احتجاجات واسعة'},{d:WAR_DAY+20,e:'انشقاق عسكري'},{d:WAR_DAY+35,e:'الحرس ينقسم'},{d:WAR_DAY+55,e:'حكومة موازية'},{d:WAR_DAY+90,e:'سقوط النظام'}]},
  {id:4,name:'تصعيد إقليمي شامل',en:'Regional Escalation',prob:12,color:'#EF4444',icon:'🔥',
   desc:'الحرب تتوسع: لبنان، العراق، اليمن. أزمة نفط عالمية وركود اقتصادي.',
   oil:'$150-200',hormuz:'مغلق تماماً',regime:'يقاتل',nuke:'خطر حقيقي',
   events:[{d:WAR_DAY+1,e:'حزب الله يصعّد'},{d:WAR_DAY+5,e:'الحوثيون ينضمون'},{d:WAR_DAY+15,e:'هجوم على ناقلة'},{d:WAR_DAY+35,e:'تدخل بري محدود'},{d:WAR_DAY+90,e:'ركود عالمي'}]},
  {id:5,name:'انسحاب أمريكي',en:'US Withdrawal',prob:8,color:'#3B82F6',icon:'🇺🇸',
   desc:'ترامب ينسحب فجأة ويعلن النصر. إسرائيل وحدها. إيران تعيد البناء.',
   oil:'$80-90',hormuz:'يفتح تدريجياً',regime:'يبقى',nuke:'يعاد بناؤه',
   events:[{d:WAR_DAY+5,e:'إعلان النصر'},{d:WAR_DAY+8,e:'سحب القوات'},{d:WAR_DAY+15,e:'آخر طلعة أمريكية'},{d:WAR_DAY+20,e:'إسرائيل منفردة'},{d:WAR_DAY+60,e:'إيران تعيد البناء'}]},
];

const GAUGE_DEFS = [
  {label:'الصواريخ الباليستية',icon:'🚀',max:2500,color:'#ef4444',key:'missiles'},
  {label:'منصات الإطلاق',icon:'📡',max:500,color:'#f59e0b',key:'launchers'},
  {label:'البرنامج النووي',icon:'☢️',max:100,color:'#a855f7',key:'nuclear_pct'},
  {label:'الدفاعات الجوية',icon:'🛡️',max:100,color:'#3b82f6',key:'airdef_pct'},
  {label:'البحرية',icon:'🚢',max:100,color:'#06b6d4',key:'navy_pct'},
];

// localStorage key
const STORAGE_KEY = 'iran_war_sim_api_key';
