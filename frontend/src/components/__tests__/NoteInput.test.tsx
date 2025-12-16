import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { NoteInput } from '../NoteInput';
import { vi } from 'vitest';

// Mock the store
const mockCreateNote = vi.fn();
const mockUploadFile = vi.fn();

vi.mock('../../stores/noteStore', () => ({
    useNoteStore: () => ({
        createNote: mockCreateNote,
        uploadFile: mockUploadFile,
        isLoading: false
    })
}));

describe('NoteInput', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders input field', () => {
        render(<NoteInput />);
        expect(screen.getByPlaceholderText("What's on your mind?")).toBeInTheDocument();
    });

    it('allows typing in the textarea', async () => {
        render(<NoteInput />);
        const input = screen.getByPlaceholderText("What's on your mind?");
        await userEvent.type(input, 'New note content');
        expect(input).toHaveValue('New note content');
    });

    it('calls createNote when form is submitted with text', async () => {
        render(<NoteInput />);
        const input = screen.getByPlaceholderText("What's on your mind?");
        const submitBtn = screen.getByText('Dump').closest('button');

        await userEvent.type(input, 'Test note');
        if (submitBtn) await userEvent.click(submitBtn);

        expect(mockCreateNote).toHaveBeenCalledWith('Test note', 'text');
    });

    it('disables submit button when empty', () => {
        render(<NoteInput />);
        const submitBtn = screen.getByText('Dump').closest('button');
        expect(submitBtn).toBeDisabled();
    });
});
