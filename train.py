
def TRAINVALTEST():
 """Function used to iterate through various hyperparameters, train the associated model, and return the optimal model

    Inputs: None

    Outputs: 
           mod:
             This is the optimal model
           ssim: numpy array
              This is an array containing the average SSIM values over the validation dataset for each hyperparameter combination
           ssimtest: Float
              This is the average SSIM over the test dataset for the combination of hyperparameters that achieves the highest/best average SSIM over the validation dataset 
"""
 import modules
 from modules import VQVAE1
 from dataset import DataProcess
 from pandas import DataFrame
 import numpy as np
 from torchmetrics import StructuralSimilarityIndexMeasure
 import torch   
 TRAINDATA,VALIDDATA,TESTDATA, DATALOADER=DataProcess() #Loading and augmenting the training data, validation data and test data
 
 
 

 DimLatSpace=np.array([10,25]) #The values of the latent space dimensionality that are iterated over
 Numberofembeddings=np.array([10,100]) #The values of 'the number of embeddings' that are iterated over
 learningrate=np.array([0.0001,0.001]) #The values of the learning rate that are iterated over
 commitcost=np.array([0.1,0.3])             #The values of the commitment cost that are iterated over
 mod=[]              #The array used to store the each model, where each model corresponds to a distinct hyperpameter combinations
 predict=np.empty((len(VALIDDATA),VALIDDATA.shape[1],VALIDDATA.shape[2],VALIDDATA.shape[3])) #array used to store the predictions of a model
 metric =StructuralSimilarityIndexMeasure(data_range=1.0,reduction='sum')  #setting up the SSIM metric
 ssim=np.empty((2,2,2,2))  #3,2,3,3                                                #array used to store the validation SSIM for each model
 
 for i in range(0,2):                                           #iterating over the hyperparameters
    for j in range(0,2):
        for z in range(0,2):
            for k in range(0,2):
             mod.append(VQVAE1(TRAINDATA,DATALOADER,DimLatSpace[i],Numberofembeddings[j],learningrate[z],commitcost[k]))
             
             for t in range(0,len(VALIDDATA)): #Predicting/reconstructing the images using the validation data set
              predict[t,:,:,:]=mod[8*i+4*j+2*z+k](VALIDDATA[t].cuda().float().reshape((1,VALIDDATA[t].shape[0],VALIDDATA[t].shape[1],VALIDDATA[t].shape[2])))[0].cpu().detach().numpy()
              #Predictions were made, one at a time, according to the line above due to memory issues that result if you try make predictions for the entire Validation dataset all at once
             ssim[i,j,z,k]=0
             torch.manual_seed(0)#This was put here rather than outside the loop, because I needed to reconstruct the results of this function using the outputs without running
             for g in range(0,int(len(VALIDDATA)/10)): #Computing the SSIM metric for each hyperparameter combination
               ssim[i,j,z,k]=metric(torch.tensor(np.float32(predict[range(g*10,(g+1)*10),:,:,:])),VALIDDATA.to(torch.float32)[range(g*10,(g+1)*10),:,:,:])+ssim[i,j,z,k]
             ssim[i,j,z,k]=ssim[i,j,z,k]/len(VALIDDATA) #issues may arise trying to compute SSIM for entire dataset all at once so the SSIM sums are calculated piecemeal
 maxssim=np.max(ssim)   #This finds the value of the best ssim
 indices=np.where(ssim==maxssim)#Finds the indices (and thus, the hyperparameter combination) associated with the best/biggest SSIM
 predict=np.empty((len(TESTDATA),TESTDATA.shape[1],TESTDATA.shape[2],TESTDATA.shape[3]))
 for t in range(0,len(TESTDATA)):  
  predict[t,:,:,:]=mod[8*indices[0][0]+4*indices[1][0]+2*indices[2][0]+indices[3][0]](TESTDATA[t].cuda().float().reshape((1,TESTDATA[t].shape[0],TESTDATA[t].shape[1],TESTDATA[t].shape[2])))[0].cpu().detach().numpy()
 ssimtest=0
 for c in range(0,int(len(TESTDATA)/4)):  #Computing the SSIM metric of the best model over the test data set
  ssimtest=metric(torch.tensor(np.float32(predict[range(c*4,(c+1)*4),:,:,:])),TESTDATA.to(torch.float32)[range(c*4,(c+1)*4),:,:,:])+ssimtest #issues may arise trying to compute SSIM for entire dataset all at once so the SSIM sums are calculated piecemeal
 ssimtest=ssimtest/len(TESTDATA) #Finds average SSIM of the best model over the testdata
 import dill as pickle
 with open('path and filename of final model', 'wb') as file:  #Saves the best model   
  pickle.dump(mod[8*indices[0][0]+4*indices[1][0]+2*indices[2][0]+indices[3][0]], file)
 return mod,ssim,ssimtest,indices 
def PredictPrior():
 """Function used to train the CNN used to generate priors,save it, and return its accuracy on the validation and test data set

    Inputs: None

    Outputs: 
           model:
             This the trained CNN used to generate priors 
           valaccuracy: numpy array
              This is the accuracy of the model when run on the encodings generated by the best VQVAE (from 'TRAINVALTEST) when run on the validation dataset
           testaccuracy: numpy array
              This is the accuracy of the model when run on the encodings generated by the best VQVAE (from 'TRAINVALTEST) when run on the test dataset
 """
 from dataset import DataProcess
 from dataset import dataencodings
 from modules import PriorCNN
 import numpy as np
 import torch.nn.functional as F
 import dill as pickle
 with open('path and finalname of final model', 'rb') as file: #loading the best VQVAE model found by running 'TRAINVALTEST' in 'train.py'
  finalmodel=pickle.load(file)
 TRAINDATA,VALIDDATA,TESTDATA,DATALOADER=DataProcess()
 trainencodings,dataloader=dataencodings(TRAINDATA) #generating and extracting the encodings(indexes for embedding vectors) of the best VQVAE model from 'TRAINVALTEST' on the trainingdata
 validencodings,dataloadervalid=dataencodings(VALIDDATA)#generating and extracting the encodings(indexes for embedding vectors) of the best VQVAE model from 'TRAINVALTEST' on the validation data
 testencodings, dataloadertest=dataencodings(TESTDATA)  #generating and extracting the encodings (indexes for embedding vectors) of the best VQVAE model from 'TRAINVALTEST on the test data
 validpredictedencodings=np.empty(validencodings.shape) #initializing the arrays which hold the predicted encodings using the CNN model from 'PRIORCNN' on the training data
 testpredictedencodings=np.empty(testencodings.shape)#initializing the arrays which hold the predicted encodings using the CNN model from 'PRIORCNN' on the validation data
 model=PriorCNN(trainencodings,dataloader,0.0001,finalmodel.embeddingdim)#initializing the arrays which hold the predicted encodings using the CNN model from 'PRIORCNN' on the test data
 for i in range(0,len(validencodings)): #This loops generates the predicted encodings using the model from 'Prior CNN' on the encodings of the best VQVAE model on the validation data
  validpredictedencodings[i,:,:]=np.argmax(F.softmax(model(validencodings[i,:,:].cuda().float().reshape((1,validencodings[i].shape[0],validencodings[i].shape[1]))),dim=1).cpu().detach().numpy(),axis=1)
 valaccuracy=np.sum(validencodings.detach().numpy()==validpredictedencodings)/(256*256*len(validencodings))#Computes the accuracy of the predicted encodings versus the encodings generated on the validationdata
 for i in range(0,len(testencodings)):#This loops generates the predicted encodings using the model from 'Prior CNN' on the encodings of the best VQVAE model on the test data
  testpredictedencodings[i,:,:]=np.argmax(F.softmax(model(testencodings[i,:,:].cuda().float().reshape((1,testencodings[i].shape[0],testencodings[i].shape[1]))),dim=1).cpu().detach().numpy(),axis=1)
 testaccuracy=np.sum(testencodings.detach().numpy()==testpredictedencodings)/(256*256*len(testencodings)) #Computes the accuracy of the predicted encodings versus the encodings generated on the testdata
 
 with open('path and filename of trained prior model', 'wb') as file:  #Saves the best model
  pickle.dump(model, file)
 return model, valaccuracy, testaccuracy