/**
 * رصد - حاجز أخطاء لعزل انهيار المكوّنات الثقيلة (الخريطة/الكرة WebGL)
 * كي لا يُسقط استثناء واحد التطبيق كله إلى شاشة بيضاء.
 *
 * صنف (class) لأن getDerivedStateFromError غير متاح للمكوّنات الدالّية، لذا
 * تُمرَّر النصوص المترجَمة عبر غلاف دالّي يستخدم useTranslation.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';

class ErrorBoundaryBase extends React.Component {
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
    const { t, fallback, children } = this.props;
    if (!this.state.hasError) return children;

    return fallback || (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-center p-6 bg-rasad-bg">
        <span className="text-3xl" aria-hidden="true">⚠️</span>
        <p className="text-sm text-slate-200">{t('error.boundaryTitle')}</p>
        <p className="text-xs text-slate-300 max-w-md break-words">
          {this.state.error?.message || t('error.unexpected')}
        </p>
        <button
          onClick={this.handleReset}
          className="mt-1 px-3 py-1.5 rounded bg-cyan-500/20 text-cyan-200 text-xs hover:bg-cyan-500/30 border border-cyan-500/30 focus-ring"
        >
          {t('error.retry')}
        </button>
      </div>
    );
  }
}

export default function ErrorBoundary(props) {
  const { t } = useTranslation();
  return <ErrorBoundaryBase {...props} t={t} />;
}
