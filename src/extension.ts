import * as vscode from 'vscode';
import axios from 'axios';
import * as fs from 'fs';
import * as path from 'path';

// Map to store AI-generated content for virtual documents
const contentMap: { [key: string]: string } = {};

class RefactorContentProvider implements vscode.TextDocumentContentProvider {
    provideTextDocumentContent(uri: vscode.Uri): string | Thenable<string> {
        return contentMap[uri.path] || '';
    }
}

export function activate(context: vscode.ExtensionContext) {
    context.subscriptions.push(
        vscode.workspace.registerTextDocumentContentProvider('refactored', new RefactorContentProvider())
    );

    const disposable = vscode.commands.registerCommand('codeRefine.runRefine', async () => {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders) {
            vscode.window.showErrorMessage('No workspace open');
            return;
        }
        const root = workspaceFolders[0].uri.fsPath;

        // Collect Python, TypeScript, JavaScript files
        let files = await vscode.workspace.findFiles('**/*.py', '**/node_modules/**');
        files = files.concat(await vscode.workspace.findFiles('**/*.ts', '**/node_modules/**'));
        files = files.concat(await vscode.workspace.findFiles('**/*.js', '**/node_modules/**'));
        if (files.length === 0) {
            vscode.window.showInformationMessage('No Python/TS/JS files found.');
            return;
        }

        // Build PlanRequest
        interface FileTreeItem { path: string; type: string; size: number; }
        interface SkeletonItem { path: string; content: string; }
        const file_tree: FileTreeItem[] = [];
        const skeletons: SkeletonItem[] = [];
        let totalSkeletonBytes = 0;

        for (const file of files) {
            const relPath = path.relative(root, file.fsPath);
            const stat = fs.statSync(file.fsPath);
            file_tree.push({ path: relPath, type: stat.isDirectory() ? 'directory' : 'file', size: stat.size });
            // Get first 50 lines as skeleton
            const doc = await vscode.workspace.openTextDocument(file);
            const lines: string[] = [];
            for (let i = 0; i < Math.min(50, doc.lineCount); i++) {
                lines.push(doc.lineAt(i).text);
            }
            const skel = lines.join('\n');
            const skelB64 = Buffer.from(skel, 'utf8').toString('base64');
            skeletons.push({ path: relPath, content: skelB64 });
            totalSkeletonBytes += Buffer.byteLength(skel, 'utf8');
        }

        const planReq = {
            request_id: new Date().toISOString(),
            workspace_root: root,
            file_tree: file_tree,
            skeletons: skeletons,
            max_skeleton_bytes: totalSkeletonBytes
        };

        // Call /plan API
        let planResp;
        try {
            planResp = await axios.post('http://localhost:8000/plan', planReq);
        } catch (err: any) {
            vscode.window.showErrorMessage(`Plan request failed: ${err}`);
            return;
        }

        const targets = planResp.data.target_files;
        if (targets.length === 0) {
            vscode.window.showInformationMessage('No files to refactor according to plan.');
            return;
        }
        const output = vscode.window.createOutputChannel('Code Refine');
        output.appendLine('Planned target files:');
        for (const tf of targets) {
            output.appendLine(`${tf.path}: ${tf.reason}`);
        }
        output.show();

        // Ask user: dry run or apply
        const choice = await vscode.window.showQuickPick(['Dry Run', 'Apply Changes'], { placeHolder: 'Select mode' });
        if (!choice) { return; }
        const dry_run = (choice === 'Dry Run');

        // Build RefactorRequest
        interface RefactorFile { path: string; content: string; }
        const refactorFiles: RefactorFile[] = [];
        for (const tf of targets) {
            const filePath = path.join(root, tf.path);
            if (fs.existsSync(filePath)) {
                const content = fs.readFileSync(filePath, 'utf8');
                const contentB64 = Buffer.from(content, 'utf8').toString('base64');
                refactorFiles.push({ path: tf.path, content: contentB64 });
            }
        }
        const refactorReq = {
            request_id: planReq.request_id,
            target_files: refactorFiles,
            research_constraints: { max_papers: 5, allowed_sources: ['arxiv', 'github'] },
            dry_run: dry_run
        };

        // Call /refactor API
        let refactorResp;
        try {
            refactorResp = await axios.post('http://localhost:8000/refactor', refactorReq);
        } catch (err: any) {
            vscode.window.showErrorMessage(`Refactor request failed: ${err}`);
            return;
        }

        // Open diffs for each result
        for (const res of refactorResp.data.results) {
            if (res.error) {
                vscode.window.showErrorMessage(`Error in ${res.path}: ${res.error}`);
                continue;
            }
            contentMap['/' + res.path] = res.new_content;
            const originalUri = vscode.Uri.file(path.join(root, res.path));
            const newUri = vscode.Uri.parse('refactored:///' + res.path);
            await vscode.commands.executeCommand('vscode.diff', originalUri, newUri, `${res.path} (AI Refactor)`);
        }
        if (!dry_run && refactorResp.data.branch) {
            vscode.window.showInformationMessage(`Changes committed on branch ${refactorResp.data.branch}`);
        }
    });

    context.subscriptions.push(disposable);
}

export function deactivate() {}