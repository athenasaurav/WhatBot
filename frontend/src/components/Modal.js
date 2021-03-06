import React from 'react';
import ReactDOM from 'react-dom';
import './stylesheets/Modal.css'

const Modal = props => {
    return ReactDOM.createPortal(
        <div onClick={props.onDismiss} className="ui dimmer modals visble active">
            <div onClick={(e) => e.stopPropagation()} className="ui standard modal visible active">
                <div className="modal-header header">{props.title}</div>
                <div className="modal-content content">
                    {props.content}
                </div>
                <div className="actions">
                    {props.actions}
                </div>
            </div>
        </div>,
        document.querySelector('#modal')
    );
};

export default Modal;