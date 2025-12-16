import * as vscode from 'vscode';
import axios from 'axios';
import * as path from 'path';

// Memory store for the "Virtual Documents"
const aiContentProvider = new Map<string, string>();

export function activate(context: vscode.ExtensionContext) {

    // 1. Register the Virtual Document Provider
    // This allows us to create URIs like 'ai-refactor:/path/to/file.py'
    // which serve content from memory, not disk.
    const provider = new class implements vscode.TextDocumentContentProvider {
        provideTextDocumentContent(uri: vscode.Uri): string {
            // lookup content by the path stored in the query or path
            return aiContentProvider.get(uri.path) || "Error: No AI content found.";
        }
    };
    context.subscriptions.push(vscode.workspace.registerTextDocumentContentProvider('ai-refactor', provider));

    // 2. Register the Command
    let disposable = vscode.commands.registerCommand('sota-coding-agent.start', async () => {
        
        const userInput = await vscode.window.showInputBox({ prompt: "How should we refactor the code?" });
        if (!userInput) return;

        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) return;
        const rootPath = workspaceFolders[0].uri.fsPath;

        // --- Phase 1: Context Gathering (Map) ---
        vscode.window.showInformationMessage("AI Refiner: Scanning File Skeletons...");
        
        const files = await vscode.workspace.findFiles('**/*.py', '**/node_modules/**');
        const skeletons = [];

        for (const file of files) {
            const doc = await vscode.workspace.openTextDocument(file);
            // Read first 50 lines only
            const head = doc.getText(new vscode.Range(0, 0, 50, 0));
            skeletons.push({
                file_path: vscode.workspace.asRelativePath(file),
                content_head: head
            });
        }

        // --- Phase 2: Planning (Backend) ---
        const planResponse = await axios.post('http://localhost:8000/plan', {
            skeletons: skeletons,
            user_instruction: userInput
        });
        
        const targetFiles: string[] = planResponse.data.target_files;
        vscode.window.showInformationMessage(`AI Refiner: Targeting ${targetFiles.length} files.`);

        // --- Phase 3: Execution (Reduce) ---
        for (const relPath of targetFiles) {
            const fileUri = vscode.Uri.file(path.join(rootPath, relPath));
            const doc = await vscode.workspace.openTextDocument(fileUri);
            const fullContent = doc.getText();

            vscode.window.setStatusBarMessage(`Refactoring ${relPath}...`);
            
            // Call Backend
            const refactorResponse = await axios.post('http://localhost:8000/refactor', {
                file_path: relPath,
                full_content: fullContent
            });

            const { refactored_code, diff } = refactorResponse.data;

            // --- Phase 4: Visualization (Virtual Doc) ---
            // Store the AI result in memory
            aiContentProvider.set(fileUri.path, refactored_code);

            // Create a URI for the "Right" side of the diff
            const aiUri = vscode.Uri.parse(`ai-refactor:${fileUri.path}`);

            // Trigger VS Code's native Side-by-Side Diff
            // Left: Local Disk File. Right: Virtual AI Stream.
            await vscode.commands.executeCommand(
                'vscode.diff',
                fileUri,
                aiUri,
                `Refactor: ${relPath}`
            );
            
            // Note: In a production app, we would add a button to "Apply"
            // which writes aiContentProvider content to fs.
        }
        
        vscode.window.setStatusBarMessage("");
    });

    context.subscriptions.push(disposable);
}

export function deactivate() {}