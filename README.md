# KubeVela Machine Learning Demo

## 安装

### 安装 KubeVela 及其 CLI

```bash
helm repo add kubevela https://charts.kubevela.net/core
helm repo update
helm install --create-namespace -n vela-system kubevela kubevela/vela-core --version 1.2.3 --wait
```

```bash
curl -fsSl https://kubevela.io/script/install.sh | bash -s 1.2.3
```

### 安装 KubeVela Machine Learning 相关插件

```bash
vela addon enable fluxcd
vela addon enable model-training
vela addon enable model-serving
```

## 将 python 代码打包成镜像

在本例中，我们将使用 [TensorFlow](https://www.tensorflow.org/) 作为我们的模型训练语言，并将其打包成镜像。

Dockerfile 如下：

```Dockerfile
# 基础镜像
FROM tensorflow/tensorflow:2.0.0-py3

# 复制代码文件
COPY /code /opt
# 复制数据集
COPY /data /opt/data

# 设置环境变量
ENV DATA_PATH="./data"
ENV TRAIN="True"
ENV VERSION="1"

WORKDIR /opt

# 如果有其他依赖，还可以安装额外依赖
# RUN pip install -r /opt/requirements.txt

# 启动命令
ENTRYPOINT ["python"]
CMD ["/opt/main.py"]
```

构建完镜像后，上传到镜像仓库
```bash
docker build -f Dockerfile -t fogdong/aidemo:v1.0 ./
docker push fogdong/aidemo:v1.0
```

## 训练模型

部署如下文件，训练本例中框架为 TensorFlow 的模型，并且将模型挂载在 PVC 中。

```yaml
apiVersion: core.oam.dev/v1beta1
kind: Application
metadata:
  name: training
  namespace: default
spec:
  components:
  - name: aidemo1
    # 指定类型为 training
    type: training
    properties:
      # 指定镜像，训练 v1 版本的模型
      image: fogdong/aidemo:v1.0
      # 指定训练的框架
      framework: tensorflow
      # 如果需要分布式训练，可以在 distribution 中指定
      # distribution:
      #   ps: 1
      #   worker: 2
      # 传入环境变量
      env:
        - name: VERSION
          value: "v1"
      # 挂载存储
      storage:
        # 如果没有已存在的 PVC，此处会自动创建一个 PVC 并进行挂载
        - name: "my-pvc"
          mountPath: "/opt/model"
        # 如果已经有一个 PVC，可以指定 PVC 挂载，如：挂在一个带有训练数据的 PVC
        # - name: "my-pvc-ref"
        #   mountPath: "/opt/data"
        #   pvcRef: "dataset"
  - name: aidemo2
    # 指定类型为 training
    type: training
    properties:
      # 指定镜像，训练 v2 版本的模型
      image: fogdong/aidemo:v2.0
      framework: tensorflow
      env:
        - name: VERSION
          value: "v2"
      storage:
        - name: "my-pvc"
          mountPath: "/opt/model"
```

## 启动模型服务

### 启动单模型的模型服务

部署如下文件，启动 PVC 中 v1 版本的模型：

```yaml
apiVersion: core.oam.dev/v1beta1
kind: Application
metadata:
  name: serving
  namespace: default
spec:
  components:
  - name: aidemo-serving
    type: serving
    properties:
      predictors:
        - name: model1
          replicas: 1
          # 指定资源
          resources:
            cpu: "1"
            memory: 2Gi
            gpu: "1"
          # 设置自动伸缩
          autoscaler: 
            minReplicas: 1
            maxReplicas: 2
            metrics:
              - type: cpu
                targetAverageUtilization: 80
          graph:
            name: my-model
            # 指定模型服务器
            implementation: tensorflow
            # 指定模型地址
            modelUri: pvc://my-pvc/v1
```

通过 `vela status` 命令，可以查看到当前模型服务的地址：

```bash
$ vela status serving --endpoint

+---------+--------------------------------+-------------------------------------------------------+
| CLUSTER |    REF(KIND/NAMESPACE/NAME)    |                       ENDPOINT                        |
+---------+--------------------------------+-------------------------------------------------------+
|         | Service/vela-system/ambassador | tcp://<ingress-ip>:80/seldon/default/aidemo-serving |
+---------+--------------------------------+-------------------------------------------------------+
```

模型的默认路由为 `api/v1.0/predictions`，可以通过 `<ingress-ip>:80/seldon/default/aidemo-serving/api/v1.0/predictions` 访问到该模型。

### 启动多模型 A/B 测试服务

部署如下文件，其中 v1 版本的模型流量设置为 75，v2 版本模型流量设置为 25。

```yaml
apiVersion: core.oam.dev/v1beta1
kind: Application
metadata:
  name: ab-serving
  namespace: default
spec:
  components:
  - name: ab-serving
    type: serving
    properties:
      predictors:
        - name: model1
          replicas: 1
          # v1 版本的模型流量为 75
          traffic: 75
          graph:
            name: my-model
            implementation: tensorflow
            modelUri: pvc://my-pvc/v1
        - name: model2
          replicas: 1
          # v2 版本的模型流量为 25
          traffic: 25
          graph:
            name: my-model
            implementation: tensorflow
            modelUri: pvc://my-pvc/v2
```

通过 `vela status` 命令，可以查看到当前模型服务的地址：

```bash
$ vela status ab-serving --endpoint

+---------+--------------------------------+-------------------------------------------------------+
| CLUSTER |    REF(KIND/NAMESPACE/NAME)    |                       ENDPOINT                        |
+---------+--------------------------------+-------------------------------------------------------+
|         | Service/vela-system/ambassador | tcp://<ingress-ip>:80/seldon/default/ab-serving |
+---------+--------------------------------+-------------------------------------------------------+
```

通过请求 `<ingress-ip>:80/seldon/default/ab-serving/api/v1.0/predictions`，可以看到，约有 75% 的流量导到了 v1 版本的模型，25% 的流量导到了 v2 版本的模型。

### 通过自定义 Header 访问多版本的模型

部署如下文件，将 v2 版本的模型设置一个 customRouting，指定 header 为 `test:test`，serviceName 指定为 v1 版本模型的组件名。

```yaml
apiVersion: core.oam.dev/v1beta1
kind: Application
metadata:
  name: routing-serving
  namespace: default
spec:
  components:
  - name: main-serving
    type: serving
    properties:
      predictors:
        - name: model1
          replicas: 1
          graph:
            name: my-model
            implementation: tensorflow
            modelUri: pvc://my-pvc/v1
  - name: test-serving
    type: serving
    properties:
      customRouting:
        # 指定自定义 Header
        header: "test: test"
        # 指定自定义路由
        serviceName: "main-serving"
      predictors:
        - name: model2
          replicas: 1
          graph:
            name: my-model
            implementation: tensorflow
            modelUri: pvc://my-pvc/v2
```


通过 `vela status` 命令，可以查看到当前模型服务的地址：

```bash
$ vela status ab-serving --endpoint

+---------+--------------------------------+-------------------------------------------------------+
| CLUSTER |    REF(KIND/NAMESPACE/NAME)    |                       ENDPOINT                        |
+---------+--------------------------------+-------------------------------------------------------+
|         | Service/vela-system/ambassador | tcp://<ingress-ip>:80/seldon/default/main-serving |
|         | Service/vela-system/ambassador | tcp://<ingress-ip>:80/seldon/default/test-serving |
+---------+--------------------------------+-------------------------------------------------------+
```

可以看到，虽然此时有两个服务地址，但是由于我们在 `customRouting` 中将第二个服务转发到第一个服务的地址当中，所以第二个服务地址被访问时会显示 404。

通过请求 `<ingress-ip>:80/seldon/default/main-serving/api/v1.0/predictions`，可以看到，在不带 Header 的情况下，流量会被导入到 v1 版本的模型；而当请求的 Header 中设置了 `test: test` 时，流量会被导入到 v2 版本的模型中。

## 训练模型 + JupyterNote Book + 模型服务

你也可以选择在一个 Application 中先训练模型，再启动一个 Jupyter Notebook 以及模型服务。

部署如下文件：

```yaml
apiVersion: core.oam.dev/v1beta1
kind: Application
metadata:
  name: simple-example
  namespace: default
spec:
  components:
  # 训练模型
  - name: demo-training
    type: training
    properties:
      image: fogdong/aidemo:v1.0
      framework: tensorflow
      env:
        - name: VERSION
          value: "v1"
      storage:
        - name: "my-pvc"
          mountPath: "/opt/model"

  # 启动 jupyter notebook
  - name: jupyter
    type: jupyter-notebook
    dependsOn:
      - demo-training
    properties:
      serviceType: LoadBalancer
      storage:
        - name: "my-pvc"
          mountPath: "/test"
  
  # 启动模型服务
  - name: demo-serving
    type: serving
    dependsOn:
      - demo-training
    properties:
      predictors:
        - name: model
          replicas: 1
          graph:
            name: my-model
            implementation: tensorflow
            modelUri: pvc://my-pvc/v1
```
