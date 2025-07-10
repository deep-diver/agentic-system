class TeamBuildingApp {
    constructor() {
        this.apiUrl = 'http://localhost:8002';
        this.sessionId = 'web_session_' + Date.now();
        this.projectsData = [];
        this.isProcessing = false;
        this.currentEventSource = null;
        
        this.initializeElements();
        this.attachEventListeners();
        this.loadProjectsData();
    }
    
    initializeElements() {
        this.projectDescription = document.getElementById('projectDescription');
        this.buildTeamBtn = document.getElementById('buildTeam');
        this.refreshProjectsBtn = document.getElementById('refreshProjects');
        this.progressSection = document.getElementById('progressSection');
        this.progressSteps = document.getElementById('progressSteps');
        this.resultsSection = document.getElementById('resultsSection');
        this.teamGrid = document.getElementById('teamGrid');
        this.projectsGrid = document.getElementById('projectsGrid');
        this.projectsCount = document.getElementById('projectsCount');
        this.loadingOverlay = document.getElementById('loadingOverlay');
    }
    
    attachEventListeners() {
        this.buildTeamBtn.addEventListener('click', () => this.buildTeam());
        this.refreshProjectsBtn.addEventListener('click', () => this.loadProjectsData());
        
        // Example prompt buttons
        document.querySelectorAll('.example-prompt').forEach(prompt => {
            prompt.addEventListener('click', () => {
                const promptText = prompt.dataset.prompt;
                this.projectDescription.value = promptText;
                this.autoResizeTextarea();
                this.updateBuildButton();
                // Auto-start team building
                setTimeout(() => this.buildTeam(), 300);
            });
        });
        
        // Auto-resize textarea
        this.projectDescription.addEventListener('input', () => {
            this.autoResizeTextarea();
            this.updateBuildButton();
        });
        
        // Enter key handling
        this.projectDescription.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && e.ctrlKey && !this.isProcessing) {
                this.buildTeam();
            }
        });
    }
    
    autoResizeTextarea() {
        this.projectDescription.style.height = 'auto';
        this.projectDescription.style.height = Math.min(this.projectDescription.scrollHeight, 200) + 'px';
    }
    
    updateBuildButton() {
        const hasText = this.projectDescription.value.trim().length > 0;
        this.buildTeamBtn.disabled = !hasText || this.isProcessing;
        
        if (this.isProcessing) {
            this.buildTeamBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Building...';
        } else {
            this.buildTeamBtn.innerHTML = '<i class="fas fa-rocket"></i> Build My Team';
        }
    }
    
    async loadProjectsData() {
        try {
            this.projectsCount.textContent = 'Loading...';
            const response = await fetch('/static/projects_data_en.json');
            this.projectsData = await response.json();
            
            this.projectsCount.textContent = `${this.projectsData.length} projects available`;
            this.displayProjects();
        } catch (error) {
            console.error('Error loading projects data:', error);
            this.projectsCount.textContent = 'Error loading projects';
        }
    }
    
    displayProjects() {
        this.projectsGrid.innerHTML = '';
        
        // Show first 20 projects to avoid overwhelming the UI
        const projectsToShow = this.projectsData.slice(0, 20);
        
        projectsToShow.forEach((project, index) => {
            const projectCard = this.createProjectCard(project, index);
            this.projectsGrid.appendChild(projectCard);
        });
    }
    
    createProjectCard(project, index) {
        const card = document.createElement('div');
        card.className = 'project-card';
        card.style.animationDelay = `${index * 50}ms`;
        
        const participantsCount = project.participants ? project.participants.length : 0;
        const rolesCount = project.required_roles ? project.required_roles.length : 0;
        
        card.innerHTML = `
            <div class="project-header">
                <h3 class="project-title">${project.project_name}</h3>
                <div class="project-meta">
                    <span><i class="fas fa-clock"></i> ${project.duration_months || 'N/A'} months</span>
                    <span><i class="fas fa-users"></i> ${participantsCount} participants</span>
                </div>
            </div>
            
            <p class="project-description">${project.descriptive_summary}</p>
            
            <div class="project-roles">
                ${project.required_roles ? project.required_roles.slice(0, 5).map(role => 
                    `<span class="role-tag">${role}</span>`
                ).join('') : ''}
                ${rolesCount > 5 ? `<span class="role-tag">+${rolesCount - 5} more</span>` : ''}
            </div>
            
            <div class="project-participants">
                <i class="fas fa-info-circle"></i> 
                ${participantsCount} team members with expertise in ${rolesCount} roles
            </div>
        `;
        
        return card;
    }
    
    async buildTeam() {
        const message = this.projectDescription.value.trim();
        if (!message || this.isProcessing) return;
        
        this.isProcessing = true;
        this.updateBuildButton();
        this.showProgressSection();
        this.hideResultsSection();
        
        try {
            await this.streamTeamBuilding(message);
        } catch (error) {
            console.error('Error building team:', error);
            this.addProgressStep('error', 'Error occurred while building team', true);
        } finally {
            this.isProcessing = false;
            this.updateBuildButton();
        }
    }
    
    async streamTeamBuilding(message) {
        return new Promise((resolve, reject) => {
            this.clearProgress();
            
            console.log('Sending message:', message);
            const url = `${this.apiUrl}/team-building/stream?${new URLSearchParams({
                message: message,
                session_id: this.sessionId
            })}`;
            console.log('Request URL:', url);
            
            this.currentEventSource = new EventSource(url);
            
            this.currentEventSource.onmessage = (event) => {
                try {
                    if (event.data === '[DONE]') {
                        this.currentEventSource.close();
                        resolve();
                        return;
                    }
                    
                    const data = JSON.parse(event.data);
                    this.handleStreamEvent(data);
                } catch (error) {
                    console.error('Error parsing SSE data:', error);
                }
            };
            
            this.currentEventSource.onerror = (error) => {
                console.error('SSE error:', error);
                console.error('EventSource readyState:', this.currentEventSource.readyState);
                
                // Add a visual error message
                this.addProgressStep('error', 'Connection error occurred', true);
                
                this.currentEventSource.close();
                reject(error);
            };
        });
    }
    
    handleStreamEvent(data) {
        console.log('Received event:', data);
        
        switch (data.type) {
            case 'progress':
                this.addProgressStep('progress', data.progress);
                break;
                
            case 'roles':
                this.addProgressStep('completed', 'Roles extracted successfully', true);
                this.showExtractedRoles(data.roles);
                break;
                
            case 'query':
                this.addProgressStep('completed', 'Query paraphrased for search', true);
                break;
                
            case 'projects':
                this.addProgressStep('completed', `Found ${data.count} similar projects`, true);
                break;
                
            case 'participants':
                this.addProgressStep('completed', 'Team suggestions generated', true);
                this.showTeamResults(data.participants);
                break;
                
            case 'final':
                this.addProgressStep('completed', 'Team building complete!', true);
                this.collapseProgressSection();
                break;
                
            case 'error':
                this.addProgressStep('error', `Error: ${data.error}`, true);
                break;
        }
    }
    
    showExtractedRoles(roles) {
        if (!roles || !roles.roles) return;
        
        const rolesStep = document.createElement('div');
        rolesStep.className = 'progress-step completed';
        rolesStep.innerHTML = `
            <div class="progress-icon">
                <i class="fas fa-check"></i>
            </div>
            <div class="progress-text">
                <strong>Required Roles:</strong>
                ${roles.roles.map(role => `<span class="role-tag">${role.role}</span>`).join(' ')}
            </div>
        `;
        this.progressSteps.appendChild(rolesStep);
    }
    
    showTeamResults(participants) {
        if (!participants || !participants.participants) return;
        
        this.showResultsSection();
        this.teamGrid.innerHTML = '';
        
        participants.participants.forEach((member, index) => {
            const memberCard = this.createTeamMemberCard(member, index);
            this.teamGrid.appendChild(memberCard);
        });
        
        // Scroll to results
        setTimeout(() => {
            this.resultsSection.scrollIntoView({ behavior: 'smooth' });
        }, 500);
    }
    
    createTeamMemberCard(member, index) {
        const card = document.createElement('div');
        card.className = 'team-member-card';
        card.style.animationDelay = `${index * 100}ms`;
        
        const initials = member.name.split(' ').map(n => n[0]).join('').toUpperCase();
        
        card.innerHTML = `
            <div class="member-header">
                <div class="member-avatar">${initials}</div>
                <div class="member-info">
                    <h3>${member.name}</h3>
                    <div class="member-role">${member.role}</div>
                </div>
            </div>
            
            <div class="member-experience">
                <i class="fas fa-briefcase"></i>
                <span>${member.experience_years} years of experience</span>
            </div>
            
            <div class="member-skills">
                ${member.skills.map(skill => 
                    `<span class="skill-tag">${skill}</span>`
                ).join('')}
            </div>
            
            ${member.reason_to_join ? `
            <div class="member-reason">
                <i class="fas fa-lightbulb"></i>
                <span>${member.reason_to_join}</span>
            </div>
            ` : ''}
        `;
        
        return card;
    }
    
    addProgressStep(type, text, completed = false) {
        const step = document.createElement('div');
        let className = 'progress-step';
        let iconContent = '';
        
        if (type === 'error') {
            className += ' error';
            iconContent = '<i class="fas fa-exclamation-triangle"></i>';
        } else if (completed) {
            className += ' completed';
            iconContent = '<i class="fas fa-check"></i>';
        } else {
            iconContent = '<i class="fas fa-circle"></i>';
        }
        
        step.className = className;
        
        step.innerHTML = `
            <div class="progress-icon">
                ${iconContent}
            </div>
            <div class="progress-text">${text}</div>
        `;
        
        this.progressSteps.appendChild(step);
        
        // Auto-scroll to latest step
        step.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    
    clearProgress() {
        this.progressSteps.innerHTML = '';
    }
    
    showProgressSection() {
        this.progressSection.style.display = 'block';
        setTimeout(() => {
            this.progressSection.scrollIntoView({ behavior: 'smooth' });
        }, 100);
    }
    
    hideProgressSection() {
        this.progressSection.style.display = 'none';
    }
    
    showResultsSection() {
        this.resultsSection.style.display = 'block';
    }
    
    hideResultsSection() {
        this.resultsSection.style.display = 'none';
    }
    
    collapseProgressSection() {
        const progressContainer = this.progressSection.querySelector('.progress-container');
        const progressSteps = this.progressSteps;
        
        // Create collapsed header
        const collapsedHeader = document.createElement('div');
        collapsedHeader.className = 'progress-collapsed-header';
        collapsedHeader.innerHTML = `
            <div class="progress-header-content">
                <i class="fas fa-cogs"></i>
                <span>Processing Complete</span>
                <span class="progress-badge">${progressSteps.children.length} steps</span>
            </div>
            <i class="fas fa-chevron-down progress-toggle-icon"></i>
        `;
        
        // Add click handler to toggle
        collapsedHeader.addEventListener('click', () => {
            const isCollapsed = progressSteps.style.display === 'none';
            progressSteps.style.display = isCollapsed ? 'block' : 'none';
            const toggleIcon = collapsedHeader.querySelector('.progress-toggle-icon');
            toggleIcon.className = isCollapsed ? 'fas fa-chevron-up progress-toggle-icon' : 'fas fa-chevron-down progress-toggle-icon';
        });
        
        // Replace the h3 with collapsed header
        const existingHeader = progressContainer.querySelector('h3');
        if (existingHeader) {
            existingHeader.replaceWith(collapsedHeader);
        }
        
        // Initially hide the steps
        progressSteps.style.display = 'none';
        
        // Add collapsed class for styling
        progressContainer.classList.add('collapsed');
    }
    
    showLoading() {
        this.loadingOverlay.style.display = 'flex';
    }
    
    hideLoading() {
        this.loadingOverlay.style.display = 'none';
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new TeamBuildingApp();
});