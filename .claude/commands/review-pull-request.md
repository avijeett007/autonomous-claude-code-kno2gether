This command will review a GitHub pull request and provide detailed feedback.

The argument should be the GitHub PR number.

Follow these steps:
1. Use the GitHub CLI to fetch detailed information about the PR
2. Get the full diff of the PR changes
3. Analyze the code changes for:
   - Code quality issues
   - Potential bugs or logical errors
   - Security concerns
   - Performance considerations
   - Adherence to project coding standards
   - Completeness of implementation
4. Generate a comprehensive review that includes:
   - An overall assessment of the PR
   - Specific feedback on each file changed
   - Suggestions for improvements
   - Questions about implementation decisions
5. Post the review as a comment on the PR using the GitHub CLI

Your review should be constructive, detailed, and helpful. Focus on making the code better rather than just pointing out issues.

The review should be helpful both to the PR author and to future developers who might read the code.

ARGUMENTS: {pr_number}