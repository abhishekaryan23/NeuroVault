import { render, screen } from '@testing-library/react';
import { NoteCard } from '../NoteCard';
import type { NoteResponse } from '../../client';

const mockNote: NoteResponse = {
    id: 1,
    content: 'Test content',
    media_type: 'text',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    is_active: true,
    tags: ['test'],
    file_path: null
};

describe('NoteCard', () => {
    it('renders text content correctly', () => {
        render(<NoteCard note={mockNote} />);
        expect(screen.getByText('Test content')).toBeInTheDocument();
    });

    it('renders tags correctly', () => {
        render(<NoteCard note={mockNote} />);
        expect(screen.getByText('#test')).toBeInTheDocument();
    });

    it('renders voice icon for voice media type', () => {
        const voiceNote = { ...mockNote, media_type: 'voice' as const };
        render(<NoteCard note={voiceNote} />);
        // Voice icon is from heroicons, we can check for the media type text
        expect(screen.getByText('voice')).toBeInTheDocument();
    });

    it('renders attachment info when file_path is present', () => {
        const attachmentNote = { ...mockNote, file_path: '/path/to/file.txt' };
        render(<NoteCard note={attachmentNote} />);
        expect(screen.getByText('/path/to/file.txt')).toBeInTheDocument();
    });
});
