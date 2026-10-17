import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import i18n from '../../i18n';
import ErrorBoundary from './ErrorBoundary';

function Boom() {
  throw new Error("Cannot read properties of undefined (reading 'secret_internal_field')");
}

describe('<ErrorBoundary>', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en');
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });
  afterEach(() => vi.restoreAllMocks());

  it('shows a generic message, never the raw exception text', () => {
    render(<ErrorBoundary><Boom /></ErrorBoundary>);
    expect(screen.getByText('This section could not be displayed.')).toBeInTheDocument();
    expect(screen.getByText('Unexpected error')).toBeInTheDocument();
    expect(document.body.textContent).not.toContain('secret_internal_field');
  });

  it('resets and calls onReset', () => {
    const onReset = vi.fn();
    render(<ErrorBoundary onReset={onReset}><Boom /></ErrorBoundary>);
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(onReset).toHaveBeenCalled();
  });
});
