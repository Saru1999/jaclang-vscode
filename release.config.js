const config = {
    branches: ['main'],
    plugins: [
        '@semantic-release/commit-analyzer',
        '@semantic-release/release-notes-generator',
        ['@semantic-release/github', { assets: [{ path: 'build/jaseci-extension.vsix', label: 'Jaseci Extension (VSIX)' }] }],
    ],
};

module.exports = config;
