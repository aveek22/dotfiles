# If you come from bash you might have to change your $PATH.
# export PATH=$HOME/bin:/usr/local/bin:$PATH

# Path to your oh-my-zsh installation.
export ZSH="$HOME/.oh-my-zsh"

# Set name of the theme to load --- if set to "random", it will
# load a random theme each time oh-my-zsh is loaded, in which case,
# to know which specific one was loaded, run: echo $RANDOM_THEME
# See https://github.com/ohmyzsh/ohmyzsh/wiki/Themes
# ZSH_THEME="robbyrussell"
ZSH_THEME="agnoster"

# Set list of themes to pick from when loading at random
# Setting this variable when ZSH_THEME=random will cause zsh to load
# a theme from this variable instead of looking in $ZSH/themes/
# If set to an empty array, this variable will have no effect.
# ZSH_THEME_RANDOM_CANDIDATES=( "robbyrussell" "agnoster" )

# Uncomment the following line to use case-sensitive completion.
# CASE_SENSITIVE="true"

# Uncomment the following line to use hyphen-insensitive completion.
# Case-sensitive completion must be off. _ and - will be interchangeable.
# HYPHEN_INSENSITIVE="true"

# Uncomment one of the following lines to change the auto-update behavior
# zstyle ':omz:update' mode disabled  # disable automatic updates
# zstyle ':omz:update' mode auto      # update automatically without asking
# zstyle ':omz:update' mode reminder  # just remind me to update when it's time

# Uncomment the following line to change how often to auto-update (in days).
# zstyle ':omz:update' frequency 13

# Uncomment the following line if pasting URLs and other text is messed up.
# DISABLE_MAGIC_FUNCTIONS="true"

# Uncomment the following line to disable colors in ls.
# DISABLE_LS_COLORS="true"

# Uncomment the following line to disable auto-setting terminal title.
# DISABLE_AUTO_TITLE="true"

# Uncomment the following line to enable command auto-correction.
# ENABLE_CORRECTION="true"

# Uncomment the following line to display red dots whilst waiting for completion.
# You can also set it to another string to have that shown instead of the default red dots.
# e.g. COMPLETION_WAITING_DOTS="%F{yellow}waiting...%f"
# Caution: this setting can cause issues with multiline prompts in zsh < 5.7.1 (see #5765)
# COMPLETION_WAITING_DOTS="true"

# Uncomment the following line if you want to disable marking untracked files
# under VCS as dirty. This makes repository status check for large repositories
# much, much faster.
# DISABLE_UNTRACKED_FILES_DIRTY="true"

# Uncomment the following line if you want to change the command execution time
# stamp shown in the history command output.
# You can set one of the optional three formats:
# "mm/dd/yyyy"|"dd.mm.yyyy"|"yyyy-mm-dd"
# or set a custom format using the strftime function format specifications,
# see 'man strftime' for details.
# HIST_STAMPS="mm/dd/yyyy"

# Would you like to use another custom folder than $ZSH/custom?
# ZSH_CUSTOM=/path/to/new-custom-folder

# Which plugins would you like to load?
# Standard plugins can be found in $ZSH/plugins/
# Custom plugins may be added to $ZSH_CUSTOM/plugins/
# Example format: plugins=(rails git textmate ruby lighthouse)
# Add wisely, as too many plugins slow down shell startup.
plugins=(git aws zsh-autosuggestions zsh-syntax-highlighting emoji dirhistory)

source $ZSH/oh-my-zsh.sh

# User configuration

# export MANPATH="/usr/local/man:$MANPATH"

# You may need to manually set your language environment
# export LANG=en_US.UTF-8

# Preferred editor for local and remote sessions
# if [[ -n $SSH_CONNECTION ]]; then
#   export EDITOR='vim'
# else
#   export EDITOR='mvim'
# fi

# Compilation flags
# export ARCHFLAGS="-arch x86_64"

# Set personal aliases, overriding those provided by oh-my-zsh libs,
# plugins, and themes. Aliases can be placed here, though oh-my-zsh
# users are encouraged to define aliases within the ZSH_CUSTOM folder.
# For a full list of active aliases, run `alias`.
#
# Example aliases
# alias zshconfig="mate ~/.zshrc"
# alias ohmyzsh="mate ~/.oh-my-zsh"
export DEFAULT_USER="aveek"
export PATH="/opt/homebrew/opt/postgresql@13/bin:$PATH"

# Adding support for Terraform from TfSwitch
export PATH="$PATH:/Users/adas/bin"

export PYENV_ROOT="$HOME/.pyenv"
command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

# JMeter Home
export JMETER_HOME="/Users/adas/applications/apache-jmeter-5.6.3/bin"
export PATH="$PATH:$JMETER_HOME"

# Adding Kafka binaries to path
export PATH="$PATH:/Users/adas/Applications/kafka_2.13-3.9.0/bin"

# Add XDG Config Variable, used by k9s skin
export XDG_CONFIG_HOME="/Users/adas/.xdg/config/"

# Adding poetry to path
export PATH="$PATH:/Users/adas/Library/Application Support/pypoetry/venv/bin"

# Terraform cache directory
export TF_PLUGIN_CACHE_DIR="$HOME/.terraform.d/plugin-cache"


# Adding Flink base path
export flink_path='/Users/adas/applications/flink-1.15.0/'
export FLINK_HOME='/Users/adas/applications/flink-1.15.0/bin/'

#Add Idea to PATH
export PATH="$PATH:/Applications/IntelliJ IDEA.app/Contents/MacOS"

# Add support for airflow development using uv and breeze
export PATH="/Users/adas/.local/bin:$PATH"


# Adding Kafka Bootstrap Servers
export TR_PROD='b-3.trackingprod.qw85m1.c6.kafka.eu-west-1.amazonaws.com:9092,b-1.trackingprod.qw85m1.c6.kafka.eu-west-1.amazonaws.com:9092,b-2.trackingprod.qw85m1.c6.kafka.eu-west-1.amazonaws.com:9092'
export TR_QA='b-1.trackingqa.wth04k.c6.kafka.eu-west-1.amazonaws.com:9092,b-3.trackingqa.wth04k.c6.kafka.eu-west-1.amazonaws.com:9092,b-2.trackingqa.wth04k.c6.kafka.eu-west-1.amazonaws.com:9092'
export PS_PROD='b-2.profile-service-prod.n0vfm2.c3.kafka.eu-west-1.amazonaws.com:9092,b-1.profile-service-prod.n0vfm2.c3.kafka.eu-west-1.amazonaws.com:9092,b-3.profile-service-prod.n0vfm2.c3.kafka.eu-west-1.amazonaws.com:9092'
export PS_QA='b-2.profile-service-test.9kbfw2.c3.kafka.eu-west-1.amazonaws.com:9092,b-3.profile-service-test.9kbfw2.c3.kafka.eu-west-1.amazonaws.com:9092,b-1.profile-service-test.9kbfw2.c3.kafka.eu-west-1.amazonaws.com:9092'

# LocalStack API Key
export LOCALSTACK_API_KEY=1fEPkBGBxu

# Adding SnowSQL Alias
alias snowsql=/Applications/SnowSQL.app/Contents/MacOS/snowsql

# Load custom aliases
source ~/dotfiles/home/.alias

# Load PlantUML GraphViz
export GRAPHVIZ_DOT=/opt/homebrew/Cellar/graphviz/13.1.1/bin/dot

# AWS SSO Utils
export AWS_DEFAULT_REGION=eu-west-1
export AWS_DEFAULT_SSO_START_URL=https://d-93677093a7.awsapps.com/start
export AWS_DEFAULT_SSO_REGION=eu-west-1

#PROFILE SERVICES specific variables
export PATH="$(brew --prefix)/opt/findutils/libexec/gnubin":$PATH
export C_INCLUDE_PATH=/opt/homebrew/Cellar/snappy/1.1.9/include:/opt/homebrew/Cellar/librdkafka/1.9.2/include:/opt/homebrew/Cellar/libpng/1.6.39/include
export LIBRARY_PATH=/opt/homebrew/Cellar/snappy/1.1.9/lib:/opt/homebrew/Cellar/librdkafka/1.9.2/lib:/opt/homebrew/Cellar/libpng/1.6.39/lib
export ARTIFACTORY_USER=`cat ~/.netrc | grep login | sed -e 's/login[[:blank:]]*//'`
export ARTIFACTORY_USERNAME=`cat ~/.netrc | grep login | sed -e 's/login[[:blank:]]*//'` # Required for CDS
export ARTIFACTORY_PASSWORD=`cat ~/.netrc | grep password | sed -e 's/password[[:blank:]]*//'`

# Tere Settings
tere() {
    local result=$(command tere "$@")
    [ -n "$result" ] && cd -- "$result"
}

#THIS MUST BE AT THE END OF THE FILE FOR SDKMAN TO WORK!!!
export SDKMAN_DIR="$HOME/.sdkman"
[[ -s "$HOME/.sdkman/bin/sdkman-init.sh" ]] && source "$HOME/.sdkman/bin/sdkman-init.sh"
# START: Added by Updated Airflow Breeze autocomplete setup
source /Users/adas/codebase/personal/contrib/airflow/dev/breeze/autocomplete/breeze-complete-zsh.sh
# END: Added by Updated Airflow Breeze autocomplete setup
