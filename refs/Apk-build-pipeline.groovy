def RUN_MODE = 'debug'
def SAST_ON = false
node('BUILD_SERVER_32') {
    env.TOOLS_PATH = "/workspace/scmtools"
    env.TOOLS_REMOTE = "ssh://git@10.21.0.32:422/cmdb/scmtools.git"
    env.TOOLS_BRANCH = "main_release"

    env.WORK_PATH = "${WORKSPACE}/${BUILD_NUMBER}"
    env.LFS_PATH = "${WORK_PATH}/local_lfs"
    env.CODE_PATH = "${WORK_PATH}/code"
    env.START_TIME = sh(returnStdout: true, script: 'date +%Y%m%d-%H%M%S').trim()

    // env.JAVA_HOME = "/usr/lib/jvm/java-8-openjdk-amd64"
    env.ANDROID_HOME = "/home/archermind/android-sdk"
    env.TMP_GRADLE_HOME = "/home/archermind/.gradle"
    env.GRADLE_OPTS = "-Dorg.gradle.jvmargs='-Xmx16g -XX:MaxMetaspaceSize=8g -XX:+HeapDumpOnOutOfMemoryError' -Dgradle.user.home=${TMP_GRADLE_HOME}"

    
    properties([
        parameters([
            string(name: 'GERRIT_EVENT_TYPE', trim: true),
            string(name: 'GERRIT_PROJECT', trim: true),
            string(name: 'GERRIT_BRANCH', trim: true),
            string(name: 'GERRIT_CHANGE_NUMBER', trim: true),
            string(name: 'GERRIT_PATCHSET_NUMBER', trim: true),
            string(name: 'GERRIT_REFSPEC', trim: true),
            string(name: 'GERRIT_CHANGE_URL', trim: true),
            string(name: 'GERRIT_CHANGE_OWNER_NAME', trim: true),
            string(name: 'GERRIT_CHANGE_OWNER_EMAIL', trim: true),
            string(name: 'GERRIT_CHANGE_SUBJECT', trim: true),
            string(name: 'NODE_LABEL', trim: true, defaultValue: 'prebuild'),
        ])
    ])
    try{
        stage("scmtools") {
            LAST_STAGE_NAME = STAGE_NAME
            
            catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
                retry(3) {
                    sh """
                        if [ -d ${TOOLS_PATH}/.git ]; then
                            cd ${TOOLS_PATH}
                            git fetch origin ${TOOLS_BRANCH}
                            git checkout ${TOOLS_BRANCH}
                            git reset --hard origin/${TOOLS_BRANCH}
                            git pull
                            git log -1
                        else
                            git clone ${TOOLS_REMOTE} -b ${TOOLS_BRANCH} ${TOOLS_PATH}
                        fi
                    """
                }
            }
        }
        stage("init job") {
            LAST_STAGE_NAME = STAGE_NAME
            sh "env && df -h"
            currentBuild.displayName =  "#${BUILD_NUMBER} > [${GERRIT_CHANGE_NUMBER} | ${GERRIT_EVENT_TYPE} | ${GERRIT_PROJECT} | ${GERRIT_BRANCH}]"

            sh """
                cat /etc/resolv.conf
            """
            sh "python3 ${TOOLS_PATH}/ci_utils/check_commit_subject.py -s \"${GERRIT_CHANGE_SUBJECT}\""
            if(RUN_MODE == 'release') {
                if(GERRIT_EVENT_TYPE in ['patchset-created', 'change-restored']) {
                    sh "python3 ${TOOLS_PATH}/ci_utils/set_gerrit_vote.py -c ${GERRIT_CHANGE_NUMBER} -r current -l Code-Review -v 0 -m '预编译开始: ${BUILD_URL} ,请稍候...' -a scm-prebuild"
                } else if(GERRIT_CHANGE_NUMBER.toInteger() > 10000) {
                    sh "python3 ${TOOLS_PATH}/ci_utils/set_gerrit_vote.py -c ${GERRIT_CHANGE_NUMBER} -r current -l Code-Review -v 0 -m '正式编译开始: ${BUILD_URL} ,请稍候...' -a os-scm"
                }
            }
            // 写入jira
            // upload_build_info()
        }
        stage("load config") {
            LAST_STAGE_NAME = STAGE_NAME
            // todo 改成获取文件先
            // config_info = loadJSON(sh(returnStdout: true, script: "python3 ${TOOLS_PATH}/ci_utils/load_git_conf_info.py -n '${GERRIT_PROJECT}' -b '${GERRIT_BRANCH}'").trim())
            // print(config_info)
            // if(GERRIT_EVENT_TYPE in ['change-merged']) {
            //     if(config_info['build_info'] && config_info['build_info'][0]['project_name'] == '') {
            //         currentBuild.result = "ABORTED"
            //         error('不属于任何产品，忽略。')
            //     }
            // }
        }
        stage("clone") {
            LAST_STAGE_NAME = STAGE_NAME
            sh "git clone --depth=1 ssh://gerrit.archermind.com.cn:29418/${GERRIT_PROJECT} -b ${GERRIT_BRANCH} ${CODE_PATH}"
            sh "cd ${CODE_PATH} && git log -2"
            sh "ls -al ${CODE_PATH}"
        }
        stage("cherrypick") {
            LAST_STAGE_NAME = STAGE_NAME
            if(GERRIT_EVENT_TYPE in  ['patchset-created', 'change-restored']) {
                try {
                    sh "python3 ${TOOLS_PATH}/ci_utils/cherrypick.py -p '${CODE_PATH}' -l ${GERRIT_CHANGE_NUMBER} -t git"
                } catch(e) {
                    sh "cd ${CODE_PATH} && git status"
                    currentBuild.result = "FAILURE"
                    error("ERROR: git cherry-pick failed!")
                }
            }
        }
        stage("prepare") {
            LAST_STAGE_NAME = STAGE_NAME
            init_android_sdk()
            if(GERRIT_EVENT_TYPE in  ['patchset-created', 'change-restored']) {
                ENV_LIST = ['Debug']
            } else {
                ENV_LIST = ['Debug', 'Release']
            }
            sh "find ${CODE_PATH} -name 'gradlew' -exec chmod +x {} ';'"
            find_gradlew = sh(returnStdout: true, script: "find ${CODE_PATH} -name 'gradlew'").trim()
            print(find_gradlew)
            if(!find_gradlew) {
                currentBuild.result = "ABORTED"
                error("ERROR: gradlew not exist!")
            }

            jdk_version = sh(returnStdout: true, script: "python3 ${TOOLS_PATH}/ci_utils/check_cicd.py").trim()
            print("jdk_version: ")
            print(jdk_version)
            if (jdk_version != "false"){
                //env.APK_SITE = "BJ"
                if(jdk_version in ["11","17"]){
                    env.JAVA_HOME = "/usr/lib/jvm/java-${jdk_version}-openjdk-amd64"
                }else if(jdk_version == "8"){
                    print("jdk is char, value is '8', will use default jdk 8 ...")
                }else{
                    print("not found jdk config on cicd.xml， will use default jdk 8")
                }
            }else{
                //env.APK_SITE = "SH"
                print("not found cicd.xml， will use default jdk ")
            }
            // find_build_gradle = sh(returnStdout: true, script: "find ${CODE_PATH} -name 'build.gradle*'").trim().split("\n|\r")
            // print(find_build_gradle)
            // for(bg_file in find_build_gradle) {
            //     sh "sed -i \"s#google()#maven { url \'https://maven.aliyun.com/repository/google\' }#g\" ${bg_file}"
            //     sh "sed -i \"s#jcenter()#maven { url \'https://maven.aliyun.com/repository/public\' }#g\" ${bg_file}"
            //     sh "sed -i \"s#mavenCentral()#maven { url \'https://maven.aliyun.com/repository/public\' }#g\" ${bg_file}"
            //     // 以下是测试转生产maven
            // }

            // find_gradle_wrapper = sh(returnStdout: true, script: "find ${CODE_PATH} -name 'gradle-wrapper.properties'").trim().split("\n|\r")
            // print(find_gradle_wrapper)
            // for(wrapper_file in find_gradle_wrapper) {
            //     print(wrapper_file)
            //     sh "sed -i 's#services.gradle.org/distributions#mirrors.cloud.tencent.com/gradle#g' ${wrapper_file}"
            //     sh "cat ${wrapper_file}"
            // }

            if(SAST_ON) {
                prepare_sast()
            }
        }
        stage("build/analysis/upload") {
            for(build_env in ENV_LIST) {
                LAST_STAGE_NAME = 'build'
                print("############################## START 【${GERRIT_PROJECT}】【${GERRIT_BRANCH}】【${build_env}】 ######################################")
                build_cmd = "cd ${CODE_PATH} && ./gradlew assemble${build_env}"
                FULL_BUILD_CMD = "${build_cmd} -x lint -x test -i -s --no-daemon"
                sh '''
                    echo "JAVA_HOME: $JAVA_HOME"
                    which java
                    which javac
                    java -version
                    javac -version

                '''
                
                if(SAST_ON) {
                    // 扫描启动时命令
                } else if(GERRIT_EVENT_TYPE == 'change-merged') {
                    retry(3) {
                        timeout(45) {
                            sh "${FULL_BUILD_CMD}"
                        }
                    }
                } else {
                    timeout(45) {
                        sh "${FULL_BUILD_CMD}"
                    }
                }
                apk_files = sh(returnStdout: true, script: "find ${CODE_PATH} -name '*.apk'").trim().split("\n|\r")
                print(apk_files.size())
                print(apk_files.join("\n"))
                if(apk_files.size() > 1) {
                    // 暂时取消
                    // error("存在多个apk，不符合规范。")
                }

                LAST_STAGE_NAME = 'analysis'
                if(SAST_ON) {
                    // 扫描启动时操作
                }

                LAST_STAGE_NAME = 'upload'
                if(GERRIT_EVENT_TYPE in ['change-merged']) {
                    try {
                        for(apk_file in apk_files) {
                            print(apk_file)
                            // 上传制品
                            // if(RUN_MODE == 'release') {
                            //     sh "python3 ${TOOLS_PATH}/ci_utils/upload_apk_to_artifactory.py $project_name $build_env $GERRIT_BRANCH $apk_file $START_TIME"
                            // }
                        }
                    } catch(e) {
                        currentBuild.result = "FAILURE"
                        error("【${GERRIT_PROJECT}】【${GERRIT_BRANCH}】【${build_env}】上传失败！！！！！")
                    }

                }
                print("【${GERRIT_PROJECT}】【${GERRIT_BRANCH}】【${build_env}】构建成功！！！！！")
            }
            
        }
    } catch(err) {
        print("Exception: ${err}")
        print("Exception Stage: ${LAST_STAGE_NAME}")
        currentBuild.result = "FAILURE"
    } finally {
        sh "rm -rf ${WORK_PATH} ${WORK_PATH}@tmp"
        print(currentBuild.currentResult)

        if(RUN_MODE == 'release') {
            if(GERRIT_EVENT_TYPE in  ['patchset-created', 'change-restored']) {
                vote = 0
                if(currentBuild.currentResult == "FAILURE") {
                    vote = -1
                } else if (currentBuild.currentResult == "SUCCESS") {
                    vote = 1
                }
                if(RUN_MODE == 'release') {
                    sh "python3 ${TOOLS_PATH}/ci_utils/set_gerrit_vote.py -c ${GERRIT_CHANGE_NUMBER} -r current -l Prebuild-Verified -v ${vote} -m '预编译【${currentBuild.currentResult}】: ${BUILD_URL}' -a scm-prebuild"
                    sh "python3 ${TOOLS_PATH}/ci_utils/gerrit_verify.py -c ${GERRIT_CHANGE_NUMBER} -b ${GERRIT_BRANCH} -s ${SAST_ON}"
                }
            } else {
                if(currentBuild.currentResult == "FAILURE") {
                    def subject = "APP-[${GERRIT_PROJECT}]构建失败，请尽快查看！"
                    def card_color = "red"
                    def body_list = [
                        "**仓库名**: ${GERRIT_PROJECT}",
                        "**分支名**: ${GERRIT_BRANCH}",
                        "**阶段名**: ${LAST_STAGE_NAME}",
                        "**PatchNum**: <a href='http://gerrit.archermind.com.cn:8080/q/${GERRIT_CHANGE_NUMBER}'>${GERRIT_CHANGE_NUMBER}</a>",
                        "**BuildJob**: <a href='${BUILD_URL}'>点此打开</a>"
                    ]
                    def body_str = body_list.join('\n')
                    // sh "python3 ${TOOLS_PATH}/ci_utils/feishu_msg.py -s '${subject}' -b '''${body_str}''' -t '${card_color}' -c 'oc_ccbf7704ab34f6f6e68539f5dedac0af'"
                }
                if(GERRIT_CHANGE_NUMBER.toInteger() > 10000) {
                    if(RUN_MODE == 'release') {
                        sh "python3 ${TOOLS_PATH}/ci_utils/set_gerrit_vote.py -c ${GERRIT_CHANGE_NUMBER} -r current -l Code-Review -v 0 -m '正式编译【${currentBuild.currentResult}】: ${BUILD_URL}' -a os-scm"
                    }
                }
            }
        }

        print("INFO: finally")
    }
}

def prepare_sast() {
    sh "python3 ${TOOLS_PATH}/ci_utils/artifactory_dowload.py -r /Coverity/cov-analysis-linux64-2023.3.0.tgz -l /workspace -u /home/os-scm"
    sh "cp -af ${COV_CONFIG_PATH} ${COV_HOME}"
    sh """
        ${COV_HOME}/bin/cov-configure --gcc
        ${COV_HOME}/bin/cov-configure --java
        ${COV_HOME}/bin/cov-configure --go
        ${COV_HOME}/bin/cov-configure --compiler ntoaarch64-gcc --comptype gcc --template
        ${COV_HOME}/bin/cov-configure --compiler aarch64-linux-android-gcc --comptype gcc --template
        ${COV_HOME}/bin/cov-configure --compiler qcc --comptype qnxcc --template
        ${COV_HOME}/bin/cov-configure --compiler q++ --comptype qnxcpp --template
        ${COV_HOME}/bin/cov-configure --compiler clang --comptype snapdragoncc --template
        ${COV_HOME}/bin/cov-configure --compiler clang++ --comptype snapdragoncxx --template
        ${COV_HOME}/bin/cov-configure --compiler arm-linux-androideabi-gcc --comptype gcc --template
    """
    print("COVERITY PROJECT: $COV_PROJECT")
    try{
        res = sh(returnStdout: true, script: "curl --location --request POST 'http://coverity.hozonauto.com:8080/api/v2/projects' --header 'Content-Type: application/json' --header 'Accept: application/json' --user osscm:Aa022100 --data '{ \"name\": \"'$COV_PROJECT'\" }' -s")
        s = loadJSON(res)['code']
        if(s == 1303) {
            print('Project already exists.')
        }
    } catch(err) {
        print(err)
    }
    try {
        res = sh(returnStdout: true, script: "curl --location --request POST 'http://coverity.hozonauto.com:8080/api/v2/streams?locale=en_us' --header 'Content-Type: application/json' --header 'Accept: application/json' --user osscm:Aa022100 --data '{\"name\": \"'$COV_PROJECT'\",\"primaryProjectName\": \"'$COV_PROJECT'\",\"triageStoreName\":\"IC\"}' -s")
        s = loadJSON(res)['code']
        if(s == 1301) {
            print('Project already exists.')
        }
    } catch(err) {
        print(err)
    }
}

def loadJSON(str) {
    if(str) {
        return readJSON(text: str)
    }else{
        error("ERROR: load json failed!")
    }
}

def init_android_sdk() {
    // sh "python3 ${TOOLS_PATH}/ci_utils/artifactory_dowload.py -r /Android_SDK/20240808/android-sdk-linux.tgz -l /workspace -u ${WORK_PATH}"
    // sh "mkdir -p ${TMP_GRADLE_HOME} && cp -f ${TOOLS_PATH}/configs/init.gradle ${TMP_GRADLE_HOME}"
    sh "mkdir -p ${ANDROID_HOME}/ndk-bundle/platforms"
    sh "ls -al ${WORK_PATH}"
}

def check_build_out(build_out, apk_files) {
    print("get build_out")
    apk_file_list = []
    origin_module_list = []
    for(apk_file in apk_files) {
        print(apk_file)
        apk_name = apk_file.split('_')[0].trim()
        apk_module = apk_name.split('/')[-1].trim()
        print(apk_module)
        if (apk_module in apk_file_list) {
            error("重复的apk文件：${apk_file}")
        } else {
            apk_file_list.add("\"${apk_module}\"")
        }
    }
    build_out_list = loadJSON(build_out)
    build_out_list.each{
        module ->
        origin_module_list.add("\"${module}\"")
    }
    apk_file_list =  apk_file_list.unique()
    if(origin_module_list.sort() == apk_file_list.sort()){
       print("apk diff is ok")
    } else {
        print(apk_file_list.sort())
        print(origin_module_list.sort())
        error("编译的apk 和指定的编译产物不一致，请检查~~~")
    }

}

def upload_build_info() {
    print("INFO: upload build info")
    sh """python3 ${TOOLS_PATH}/ci_utils/upload_build_info.py -n '${JOB_NAME}' -b '${BUILD_NUMBER}' -u '${BUILD_URL}' -s '${GERRIT_CHANGE_SUBJECT.replace("'", "'\\''")}'"""
}

