import tensorflow as tf
import argparse
from data_api import *


# mnist = tf.keras.datasets.mnist
# (x_train, y_train), (x_test, y_test) = mnist.load_data()
# x_train, x_test = x_train / 255.0, x_test / 255.0

def _build_model():
    # model = tf.keras.models.Sequential([
    #   tf.keras.layers.Flatten(input_shape=(28, 28)),
    #   tf.keras.layers.Dense(128, activation='relu'),
    #   tf.keras.layers.Dropout(0.2),
    #   tf.keras.layers.Dense(10, activation='softmax')
    # ])

    model = tf.keras.models.Sequential([
      tf.keras.layers.Flatten(input_shape=(28, 28)),
      tf.keras.layers.Dropout(0.95),
      tf.keras.layers.Dense(10, activation='softmax')
    ])
    return model


def train(model_save_path, data_path):
    """

    :param model_save_path: 保存模型的地址
    """
    path = '/Users/dongshandong/codes/kube_vela_demo/data/'
    x_train, y_train, x_test, y_test = load_data(data_path)

    # build model & train
    model = _build_model()
    model.compile(optimizer='adam',
                  loss='sparse_categorical_crossentropy',
                  metrics=['accuracy'])

    model.fit(x_train, y_train, epochs=5)
    model.save(model_save_path)
    return True


def update(model_load_path, x_update, y_update, model_save_path):
    """

    :param model_load_path: 加载base model的路径地址
    :param x_update: 更新数据集的X
    :param y_update:更新数据集的Y
    :param model_save_path: 新模型保存地址
    :return:
    """

    # build model & train
    model = tf.keras.models.load_model(model_load_path)

    model.compile(optimizer='adam',
                  loss='sparse_categorical_crossentropy',
                  metrics=['accuracy'])

    model.fit(x_update, y_update, epochs=5)
    model.save(model_save_path)
    return True

def predict(model_path,X):
    """

    :param model_path: 模型保存地址路径，进行加载
    :param X: 待服务的输入数据
    :return:
    """
    # load model
    model = tf.keras.models.load_model(model_path)
    Y = model.predict(X)
    Y= tf.argmax(Y, 1)

    Y = tf.keras.backend.eval(Y)
    print(Y)
    return Y



if __name__ == '__main__':
    # load data
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', type=str, default = os.environ.get('DATA_PATH'))
    parser.add_argument('--train', type=bool, default = os.environ.get('TRAIN'))
    parser.add_argument('--version', type=str, default = os.environ.get('VERSION'))
    args = parser.parse_args()
    x_train, y_train, x_test, y_test = load_data(args.path)

    # build model & train
    model = _build_model()
    model_path = './model/' + args.version + '/1/'
    if args.train:
        model.compile(optimizer='adam',
                      loss='sparse_categorical_crossentropy',
                      metrics=['accuracy'])

        model.fit(x_train, y_train, epochs=0)
        model.save(model_path)
    else:
        # load model
        model = tf.keras.models.load_model(model_path)

    predict(model_path,x_test)