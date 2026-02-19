import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET(
    request: Request,
    { params }: { params: { filename: string } }
) {
    try {
        const filename = params.filename;

        // output 디렉토리에서 JSON 파일 읽기
        const outputDir = path.join(process.cwd(), '..', 'output');
        const filePath = path.join(outputDir, filename);

        if (!fs.existsSync(filePath)) {
            return NextResponse.json(
                { error: 'Newsletter not found' },
                { status: 404 }
            );
        }

        const content = fs.readFileSync(filePath, 'utf-8');
        const data = JSON.parse(content);

        return NextResponse.json(data);
    } catch (error) {
        console.error('Error reading newsletter:', error);
        return NextResponse.json(
            { error: 'Failed to read newsletter' },
            { status: 500 }
        );
    }
}
