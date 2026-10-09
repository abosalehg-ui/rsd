import { describe, it, expect, vi } from 'vitest';
import React, { useRef } from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { useModal, modalDepth } from './useModal';

function Layer({ name, open = true, onClose, trap = true }) {
  const ref = useRef(null);
  const first = useRef(null);
  useModal(open, onClose, { containerRef: ref, initialFocusRef: first, trap });
  if (!open) return null;
  return (
    <div ref={ref} role="dialog" aria-label={name}>
      <button ref={first}>{`${name} first`}</button>
      <button>{`${name} last`}</button>
    </div>
  );
}

describe('useModal', () => {
  it('closes only the topmost layer on Escape', () => {
    const closeDrawer = vi.fn();
    const closeModal = vi.fn();
    const { rerender } = render(<><Layer name="drawer" onClose={closeDrawer} trap={false} /><Layer name="modal" onClose={closeModal} /></>);
    expect(modalDepth()).toBe(2);

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(closeModal).toHaveBeenCalledTimes(1);
    expect(closeDrawer).not.toHaveBeenCalled();

    // بعد إغلاق النافذة تصير الدرج هي العليا
    rerender(<><Layer name="drawer" onClose={closeDrawer} trap={false} /><Layer name="modal" open={false} onClose={closeModal} /></>);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(closeDrawer).toHaveBeenCalledTimes(1);
    expect(closeModal).toHaveBeenCalledTimes(1);
  });

  it('focuses the initial element and restores focus on close', () => {
    const { rerender } = render(<><button>opener</button></>);
    screen.getByText('opener').focus();
    rerender(<><button>opener</button><Layer name="modal" onClose={() => {}} /></>);
    expect(screen.getByText('modal first')).toHaveFocus();
    rerender(<><button>opener</button><Layer name="modal" open={false} onClose={() => {}} /></>);
    expect(screen.getByText('opener')).toHaveFocus();
    expect(modalDepth()).toBe(0);
  });

  it('traps Tab inside a modal layer', () => {
    render(<><button>outside</button><Layer name="modal" onClose={() => {}} /></>);
    const first = screen.getByText('modal first');
    const last = screen.getByText('modal last');
    last.focus();
    fireEvent.keyDown(document, { key: 'Tab' });
    expect(first).toHaveFocus();
    fireEvent.keyDown(document, { key: 'Tab', shiftKey: true });
    expect(last).toHaveFocus();
    // تركيز تسرّب خارج الطبقة يعود إليها
    screen.getByText('outside').focus();
    fireEvent.keyDown(document, { key: 'Tab' });
    expect(first).toHaveFocus();
  });

  it('leaves Tab alone for a non-trapping layer', () => {
    render(<Layer name="drawer" onClose={() => {}} trap={false} />);
    const last = screen.getByText('drawer last');
    last.focus();
    const ev = new KeyboardEvent('keydown', { key: 'Tab', bubbles: true, cancelable: true });
    document.dispatchEvent(ev);
    expect(ev.defaultPrevented).toBe(false);
  });
});
