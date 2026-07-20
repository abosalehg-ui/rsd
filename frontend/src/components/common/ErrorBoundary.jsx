/**
 * رصد - حاجز أخطاء لعزل انهيار المكوّنات الثقيلة (الخريطة/الكرة WebGL)
 * كي لا يُسقط استثناء واحد التطبيق كله إلى شاشة بيضاء.
 */
import React from 'react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error('ErrorBoundary caught:', error, info);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    this.props.onReset?.();
  };

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-center p-6 bg-[#0a0e17]">
            <span className="text-3xl">⚠️</span>
            <p className="text-sm text-slate-300">تعذّر عرض هذا الجزء.</p>
            <p className="text-[11px] text-slate-500 max-w-md break-words">
              {this.state.error?.message || 'خطأ غير متوقّع'}
            </p>
            <button
              onClick={this.handleReset}
              className="mt-1 px-3 py-1.5 rounded bg-cyan-500/20 text-cyan-300 text-xs hover:bg-cyan-500/30 border border-cyan-500/30"
            >
              إعادة المحاولة
            </button>
          </div>
        )
      );
    }
    return this.props.children;
  }
}
