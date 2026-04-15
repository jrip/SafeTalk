import { Modal, type ModalProps } from "antd";
import { useCallback, useRef, useState, type ReactNode } from "react";
import Draggable, { type DraggableData, type DraggableEvent } from "react-draggable";

/**
 * Modal Ant Design с перетаскиванием за шапку (`.ant-modal-header`).
 */
export function DraggableModal({ styles, ...rest }: ModalProps) {
  const [bounds, setBounds] = useState({ left: 0, top: 0, bottom: 0, right: 0 });
  const draggleRef = useRef<HTMLDivElement>(null);

  const onStart = useCallback((_event: DraggableEvent, uiData: DraggableData) => {
    const { clientWidth, clientHeight } = window.document.documentElement;
    const targetRect = draggleRef.current?.getBoundingClientRect();
    if (!targetRect) {
      return;
    }
    setBounds({
      left: -targetRect.left + uiData.x,
      right: clientWidth - (targetRect.right - uiData.x),
      top: -targetRect.top + uiData.y,
      bottom: clientHeight - (targetRect.bottom - uiData.y),
    });
  }, []);

  const mergedStyles: ModalProps["styles"] = {
    ...styles,
    header:
      typeof styles?.header === "object" && styles.header !== null && !Array.isArray(styles.header)
        ? { cursor: "move", ...styles.header }
        : { cursor: "move" },
  };

  const modalRender = useCallback(
    (modal: ReactNode) => (
      <Draggable bounds={bounds} nodeRef={draggleRef} onStart={onStart} handle=".ant-modal-header">
        <div ref={draggleRef}>{modal}</div>
      </Draggable>
    ),
    [bounds, onStart],
  );

  return <Modal {...rest} styles={mergedStyles} modalRender={modalRender} />;
}
